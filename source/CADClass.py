#CADClass.py
#Description:   Base HEAT CAD module
#Engineer:      T Looby
#Date:          20191107
#
#
#THIS MODULE IS FROM HEAT, AND AS SUCH IS PROTECTED UNDER THE MIT LICENSE!
#USERS MUST ATTRIBUTE THE SOURCE CODE
#See https://github.com/plasmapotential/HEAT for more information

import sys
import os

#this happens in launchHEAT.py as of HEAT v2.0, but left here for reference
#you need to do this before running this module
#FREECADPATH = '/opt/freecad/appImage/squashfs-root/usr/lib'
#oldpath = sys.path
#sys.path.append(FREECADPATH)
#sys.path = [FREECADPATH]

import FreeCAD
#set compound merge on STP imports to Off
FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Import/hSTEP").SetBool("ReadShapeCompoundMode", False)
import Part
import Mesh

import MeshPart
#sys.path = oldpath
import Import
import Fem
import stl


import time
import numpy as np
import pandas as pd

import toolsClass
tools = toolsClass.tools()

import logging
log = logging.getLogger(__name__)

import open3d as o3d



class CAD:
    """
    General CAD class

    Inputs:
    mode    GUI or CMD
    infile  input file in CSV format with each variable on a new line:
            variable, value

    Generally, there are part objects, which correspond to parts from an STEP
    (ISO 10303-21) file.  There are also mesh objects, which correspond to a
    mesh from an STL file.  The region of interest (ROI) is a list of part
    numbers that we are interested in.  When we get a ROI, we then build
    corresponding part (self.ROIparts), mesh (self.ROImeshes), face normal
    (self.ROInorms), and face center (self.ROIctrs) objects, which correspond
    to the ROI list by index.

    Maybe this picture will help:

                            ROI
                    _________|_______________
                   /     /       \     \     \
                parts  meshes   ctrs  norms  areas


    """
    def __init__(self, rootDir=None, dataPath=None, chmod=0o774, UID=-1, GID=-1):
        """
        rootDir is root HEAT source code directory
        dataPath is the location where we write all output to
        """
        self.rootDir = rootDir
        tools.rootDir = self.rootDir
        self.dataPath = dataPath
        tools.dataPath = self.dataPath
        self.chmod = chmod
        self.GID = GID
        self.UID = UID
        
        # total extent of the CAD; set by self.minmaxExtent()
        self.Rmin = None
        self.Rmax = None
        self.Zmin = None
        self.Zmax = None

        return

    def setupNumberFormats(self, tsSigFigs=6, shotSigFigs=6):
        """
        sets up pythonic string number formats for shot and timesteps
        """
        self.tsFmt = "{:."+"{:d}".format(tsSigFigs)+"f}"
        self.shotFmt = "{:0"+"{:d}".format(shotSigFigs)+"d}"
        return

    def loadPath(self, path):
        """
        appends path to system environment PYTHONPATH
        """
        sys.path.append(path)
        return



    def allowed_class_vars(self):
        """
        .. Writes a list of recognized class variables to HEAT object
        .. Used for error checking input files and for initialization

        CAD Variables:
        --------------

        :gridRes:  can be a number in [mm] or 'standard'.  Defines the intersection mesh
          grid resolution.  If set to a number, uses Mefisto mesher to generate
          a mesh with triangle edge lengths smaller than number.  If set to 
          standard, uses the FreeCAD standard mesher.  Recommended to use standard
          unless you know what you are doing.
        :overWrite: can be True or False.  If True, overWrite existing STPs and STLs.
          If False, recycle previous CAD unless there is a timestep mismatch.
        :xT: global translation of entire ROI in x direction [mm]
        :yT: global translation of entire ROI in y direction [mm]
        :zT: global translation of entire ROI in z direction [mm]

        """


        self.allowed_vars = [
                            'gTx',
                            'gTy',
                            'gTz',
                            'gridRes',
                            'overWriteMask'
                            ]
        return

    def setTypes(self):
        """
        Nothing to do for this class
        """
        return


    def getROI(self, timestepMap):
        """
        Writes ROI as list to CAD object.  Input is timestepMap dataframe
        which is read by function in PFCClass.
        """
        self.ROI = timestepMap['PFCname'].values
        #self.ROIList = list(set(self.ROI)) #does not preserve order
        self.ROIList = list(self.ROI)
        self.ROIparts = ['None' for i in range(len(self.ROI))]
        self.ROImeshes = ['None' for i in range(len(self.ROI))]
        self.ROIctrs = ['None' for i in range(len(self.ROI))]
        self.ROInorms = ['None' for i in range(len(self.ROI))]
        res = timestepMap['resolution'].values
        self.ROIresolutions = []
        for x in res:
            if isinstance(x, (np.floating, float, int, np.integer)):
                self.ROIresolutions.append(x)
            else:
                self.ROIresolutions.append(x.strip())
        return

    def getGyroSources(self, gyroSources):
        """
        Writes GyroSources as list to CAD object.  Input is timestepMap dataframe
        which is read by function in PFCClass.
        """
        #self.ROIList = list(set(self.ROI)) #does not preserve order
        self.gyroSources = list(gyroSources)
        self.gyroParts = ['None' for i in range(len(self.gyroSources))]
        self.gyroMeshes = ['None' for i in range(len(self.gyroSources))]
        self.gyroCtrs = ['None' for i in range(len(self.gyroSources))]
        self.gyroNorms = ['None' for i in range(len(self.gyroSources))]
        self.gyroAreas = ['None' for i in range(len(self.gyroSources))]
        return

    def getIntersectsFromFile(self, timestepMap):
        """
        Writes intersections to CAD object
        """
        self.ROImapDirections = []
        self.ROIintersects = []

        #parse intersects column and make indexed list of intersection parts
        # for each ROI part
        for row in timestepMap['intersectName']:
            self.ROIintersects.append(row.split(':'))

        #list of unique intersect parts
        self.intersectList = list(set( [j for row in self.ROIintersects for j in row] ))

        #if user defined 'all' in PFC file
        includeTags = ['all','All',' all', ' All', 'ALL']
        if sum([x in includeTags for x in self.intersectList]) > 0:
            #initialize intersect variables for all parts in STP file
            self.intersectParts = ['None' for i in range(len(self.CADparts))]
            self.intersectMeshes = ['None' for i in range(len(self.CADparts))]
            self.intersectCtrs = ['None' for i in range(len(self.CADparts))]
            self.intersectNorms = ['None' for i in range(len(self.CADparts))]
            self.intersectList = [obj.Label for obj in self.CADparts]
        else:
            #initialize intersect variables defined in file
            self.intersectParts = ['None' for i in range(len(self.intersectList))]
            self.intersectMeshes = ['None' for i in range(len(self.intersectList))]
            self.intersectCtrs = ['None' for i in range(len(self.intersectList))]
            self.intersectNorms = ['None' for i in range(len(self.intersectList))]

        return


    def readMesh(self, file):
        """
        reads a mesh file, returns mesh object
        """
        mesh = Mesh.Mesh(file)
        return mesh

    def getROImeshes(self, resolution=None):
        """
        Checks to see if STLs at desired resolution exist.  If they do, load em.
        If they don't, create them.

        BYOM = Bring Your Own Mesh.  This will be set to True when using
        terminal user interface if PFC csv file has an STL instead of
        a part name in the PFCname column.  To BYOM, place the stl file
        in the HEATrun directory and modify the PFC csv file.
        """
        self.BYOM = False
        for idx,partnum in enumerate(self.ROI):

            #user supplied STL file ( Bring Your Own Mesh (BYOM) )
            _, extension = os.path.splitext(partnum)
            if extension == '.stl':
                print("Using user supplied mesh")
                log.info("Using user supplied mesh")
                #load mesh from file
                self.BYOM=True
                self.loadROIMesh(self.machInDir + partnum, idx)
            #use HEAT generated mesh 
            else:
                #if BYOM was previously set to True, user is trying to mix user supplied
                #meshes with the HEAT meshing algorithm -> not supported
                if self.BYOM == True:
                    print("\n===Meshing Error:===")
                    print("You cannot mix user supplied meshes with the HEAT meshing algs.")
                    print("Either change your PFC file so that all PFCnames correspond")
                    print("to user supplied mesh objects (ie suffix .stl), or change")
                    print("your PFC file so that all PFCnames correspond to STEP file") 
                    print("object names (not .stls) for HEAT meshing.")
                    print("Exiting...\n")
                    log.info("\n===Meshing Error:===")
                    log.info("You cannot mix user supplied meshes with the HEAT meshing algs.")
                    log.info("Either change your PFC file so that all PFCnames correspond")
                    log.info("to user supplied mesh objects (ie suffix .stl), or change")
                    log.info("your PFC file so that all PFCnames correspond to STEP file") 
                    log.info("object names (not .stls)  for HEAT meshing.")
                    log.info("Exiting...\n")
                    sys.exit()
                if resolution == None:
                    if type(self.ROIresolutions[idx]) == str:
                        resolution = self.ROIresolutions[idx]
                    else:
                        resolution = float(self.ROIresolutions[idx])

                #standard meshing algorithm
                if type(resolution) == str:
                    name = self.STLpath + partnum + "___"+resolution+".stl".format(resolution)
                #mefisto meshing algorithm
                else:
                    name = self.STLpath + partnum + "___{:.6f}mm.stl".format(resolution)

                if os.path.exists(name) and self.overWriteMask == False:
                    print("Mesh exists, loading...")
                    self.loadROIMesh(name,idx)
                else:
                    print("New mesh.  Creating...")
                    self.ROIobjFromPartnum(partnum,idx)


        #global mesh translations if requested
        for i,mesh in enumerate(self.ROImeshes):
            self.ROImeshes[i] = self.globalMeshTranslation(mesh)

        #Now get face centers, normals, areas
        self.ROInorms,self.ROIctrs,self.ROIareas = self.normsCentersAreas(self.ROImeshes)
        return

    def getIntersectMeshes(self, resolution=None):
        """
        Checks to see if STLs at desired resolution exist.  If they do, load em.
        If they don't, create them.
        """
        if resolution == None:  resolution=self.gridRes
        for partnum in self.intersectList:
            #user supplied STL file ( Bring Your Own Mesh (BYOM) )
            _, extension = os.path.splitext(partnum)
            if extension == '.stl':
                print("Using user supplied mesh")
                log.info("Using user supplied mesh")
                #load mesh from file
                self.loadIntersectMesh(self.machInDir + partnum)                   

            #use HEAT generated mesh 
            else:
                #if BYOM was previously set to True, user is trying to mix user supplied
                #meshes with the HEAT meshing algorithm -> not supported
                if self.BYOM == True:
                    print("\n===Meshing Error:===")
                    print("You cannot mix user supplied meshes with the HEAT meshing algs.")
                    print("Either change your PFC file so that all PFCnames correspond")
                    print("to user supplied mesh objects (ie suffix .stl), or change")
                    print("your PFC file so that all PFCnames correspond to STEP file") 
                    print("object names (not .stls) for HEAT meshing.")
                    print("Exiting...\n")
                    log.info("\n===Meshing Error:===")
                    log.info("You cannot mix user supplied meshes with the HEAT meshing algs.")
                    log.info("Either change your PFC file so that all PFCnames correspond")
                    log.info("to user supplied mesh objects (ie suffix .stl), or change")
                    log.info("your PFC file so that all PFCnames correspond to STEP file") 
                    log.info("object names (not .stls)  for HEAT meshing.")
                    log.info("Exiting...\n")
                    sys.exit()
                #standard meshing algorithm
                if type(resolution) == str:
                    name = self.STLpath + partnum + "___"+resolution+".stl".format(resolution)
                #mefisto meshing algorithm
                else:
                    name = self.STLpath + partnum + "___{:.6f}mm.stl".format(resolution)

                if os.path.exists(name) and self.overWriteMask == False:
                    print("Intersect mesh exists, loading...")
                    log.info("Intersect mesh exists, loading...")
                    self.loadIntersectMesh(name)
                else:
                    print("New intersect mesh.  Creating "+partnum)
                    log.info("New intersect mesh.  Creating "+partnum)
                    self.intersectObjFromPartnum(partnum, resolution)

        #global mesh translations if requested
        for i,mesh in enumerate(self.intersectMeshes):
            self.intersectMeshes[i] = self.globalMeshTranslation(mesh)

        #Now get face centers, normals, areas
        self.intersectNorms,self.intersectCtrs,self.intersectAreas = self.normsCentersAreas(self.intersectMeshes,bndybox = True)
        return

    def getGyroSourceMeshes(self, resolution=None):
        """
        Checks to see if STLs at desired resolution exist.  If they do, load em.
        If they don't, create them.
        """
        if resolution == None:  resolution=self.ROIGridRes
        for idx,partnum in enumerate(self.gyroSources):
            name = self.STLpath + partnum + "___" + resolution +"mm.stl"
            if os.path.exists(name) and self.overWriteMask == False:
                print("Mesh exists, loading...")
                self.loadGyroMesh(name,idx)
            else:
                print("New mesh.  Creating...")
                self.gyroParts[idx], self.gyroMeshes[idx] = self.objFromPartnum(partnum,idx)

        #Now get face centers, normals, areas
        self.gyroNorms,self.gyroCtrs,self.gyroAreas = self.normsCentersAreas(self.gyroMeshes)
        return

    def ROIobjFromPartnum(self, partslist, idx):
        """
        Generates ROI objects from list of part numbers.
        """
        #Check if this is a single file or list and make it a list
        if type(partslist) == str:
            partslist = [partslist]
        #Build a list of parts CAD objects
        parts = []
        for part in partslist:
#            idx = np.where(np.asarray(self.ROI) == part)[0][0]
            count = 0
            for i in range(len(self.CADparts)):
                if part == self.CADparts[i].Label:
                    count += 1
                    self.ROIparts[idx] = self.CADparts[i]
                    if type(self.ROIresolutions[idx]) == str:
                        self.ROImeshes[idx] = self.part2meshStandard(self.ROIparts[idx])[0]
                    else:
                        self.ROImeshes[idx] = self.part2mesh(self.ROIparts[idx], self.ROIresolutions[idx])[0]

            if count == 0:
                print("Part "+part+" not found in CAD.  Cannot Mesh!")
                log.info("Part "+part+" not found in CAD.  Cannot Mesh!")
        return

    def intersectObjFromPartnum(self, partslist, resolution):
        """
        Generates intersect objects from list of part numbers.

        if resolution is 'standard' then generates mesh using FreeCAD
        Standard algorithm
        """
        #Check if this is a single file or list and make it a list
        if type(partslist) == str:
            partslist = [partslist]
        #Build a list of parts CAD objects
        parts = []
        for part in partslist:
            count = 0
            idx = np.where(np.asarray(self.intersectList) == part)[0][0]
            for i in range(len(self.CADparts)):
                if part == self.CADparts[i].Label:
                    count += 1
                    self.intersectParts[idx] = self.CADparts[i]
                    if resolution=="standard":
                        self.intersectMeshes[idx] = self.part2meshStandard(self.intersectParts[idx])[0]
                    else:
                        self.intersectMeshes[idx] = self.part2mesh(self.intersectParts[idx], resolution=resolution)[0]

            if count == 0:
                print("Part "+part+" not found in CAD.  Cannot Mesh!")
                log.info("Part "+part+" not found in CAD.  Cannot Mesh!")

        return

    def objFromPartnum(self, partslist, idx):
        """
        Generates objects from list of part names.
        """
        #Check if this is a single file or list and make it a list
        if type(partslist) == str:
            partslist = [partslist]
        #Build a list of parts CAD objects
        parts = []
        meshes = []
        for part in partslist:
#            idx = np.where(np.asarray(self.ROI) == part)[0][0]
            count = 0
            for i in range(len(self.CADparts)):
                if part == self.CADparts[i].Label:
                    count += 1
                    parts.append(self.CADparts[i])
                    meshes.append(self.part2meshStandard(self.CADparts[i])[0])

            if count == 0:
                print("Part "+part+" not found in CAD.  Cannot Mesh!")
                log.info("Part "+part+" not found in CAD.  Cannot Mesh!")
        return parts, meshes

    def loadSTEP(self):
        """
        Loads CAD STEP (ISO 10303-21) file into object

        (Also loads other file formats, including .FCStd)
        """
        print("Loading STEP file...")
        log.info("Loading STEP file...")
        
        #check if we are loading a STEP file or a native FreeCAD file
        _, file_extension = os.path.splitext(self.STPfile)
        if file_extension == '.FCStd':
            self.CAD = FreeCAD.open(self.STPfile)
        else:
            self.CAD = Import.open(self.STPfile)

        self.CADdoc = FreeCAD.ActiveDocument
        #Coordinate permutation if necessary
        if self.permute_mask=='True' or self.permute_mask == True:
            self.permuteSTEP()
            #self.permuteSTEPAssy()
            self.permute_mask = False

        #Save all parts/objects
        self.CADobjs = self.CADdoc.Objects
        self.CADparts = []
        for obj in self.CADobjs:
            if type(obj) == Part.Feature:
                self.CADparts.append(obj)
            else:
                print("Part "+obj.Label+" not Part.Feature.  Type is "+str(type(obj)))

        print("Loaded STEP file: " + self.STPfile)
        log.info("Loaded STEP file: " + self.STPfile)
        return

    def saveSTEP(self, file, objs):
        """
        Saves CAD STEP (ISO 10303-21) file

        objs    CAD objects.  If you want to preserve Assembly architecture
                then you need to only save [FreeCAD.ActiveDocument.ASSEMBLY].
                Otherwise each part should be in a list
        file    filename to save into
        """
        try:
            Import.export(objs, file)
            print("Saved new STEP file: " + file)
        except OSError as e:
            print("Error saving STEP file.  Aborting.")
            print(e)
        return

    def loadBREP(self):
        """
        Loads BREP Open Cascade file
        """
        print("Loading BREP file...")
        log.info("Loading BREP file...")
        self.CAD = Part.open(self.BREPfile)
        self.CADdoc = FreeCAD.ActiveDocument
        #Coordinate permutation if necessary
        if self.permute_mask=='True' or self.permute_mask == True:
            self.permuteSTEP()
            #self.permuteSTEPAssy()
            self.permute_mask = False

        #Save all parts/objects
        self.CADobjs = self.CADdoc.Objects
        self.CADparts = []
        for obj in self.CADobjs:
            if type(obj) == Part.Feature:
                self.CADparts.append(obj)

        print("Loaded BREP file: " + self.BREPfile)
        log.info("Loaded BREP file: " + self.BREPfile)
        return

    def saveBREP(self, file, objs):
        """
        Saves BREP file

        objs    CAD objects.  If you want to preserve Assembly architecture
                then you need to only save [FreeCAD.ActiveDocument.ASSEMBLY].
                Otherwise each part should be in a list
        file    filename to save into
        """
        try:
            Part.export(objs ,file)
            print("Saved new BREP file: " + file)
        except OSError as e:
            print("Error saving STEP file.  Aborting.")
            print(e)
        return

    def permuteSTEPAssy(self):
        """
        Cyclic permutation on STPfile assembly preserving right hand rule
        works on assemblies
        """
        ang = 90.0
        #here we assume we received CAD from NSTXU engineers who have y-axis vertical
        axis = FreeCAD.Vector(1,0,0)
        rot = FreeCAD.Rotation(axis,ang)
        if self.assembly_mask:
            self.CADdoc.ASSEMBLY.Placement = FreeCAD.Placement(axis,rot)
        print("CAD Permutation Complete")
        log.info("CAD Permutation Complete")
        return

    def permuteSTEP(self):
        """
        Cyclic permutation on STPfile assembly preserving right hand rule
        Works on individual parts
        """
        rot = FreeCAD.Placement( FreeCAD.Vector(0,0,0), FreeCAD.Rotation(0,0,90) )
        for obj in FreeCAD.ActiveDocument.Objects:
            if type(obj) == Part.Feature:
                obj.Placement = rot.multiply(obj.Placement)
        print("CAD Permutation Complete")
        log.info("CAD Permutation Complete")
        return

    def getLabels(self, parts):
        """
        Gets labels from a list of CAD parts and returns a list of labels
        """
        #Check if this is a single part or list and make it a list
        if type(parts) != list:
            parts = [parts]
        labels = []
        for part in parts:
            labels.append(part.Label)
        return labels

    def part2mesh(self, part, resolution, mode='fine'):
        """
        Converts CAD object to mesh object, and adds mesh object to CAD document
        if part is a list of objects, returns a list of meshes.
        If part isn't a list, freecad throws an error.  Use this to determine
        if part is a list of parts or a single object, and handle each case
        correctly.  Returns a list of mesh objects

        This function uses the FreeCAD Mefisto algorithm, and defines mesh
        by maximum edge length (resolution)
        """
        resolution = float(resolution)
        #Check if this is a single file or list and make it a list
        if type(part) != list:
            part = [part]
        meshes = []
        for i in range(len(part)):
            shape = part[i].Shape.copy(False)
            shape.Placement = part[i].getGlobalPlacement()
            print('Meshing part ' + part[i].Label)
            log.info('Meshing part ' + part[i].Label)
            mesh = MeshPart.meshFromShape(shape, MaxLength=resolution)
            meshes.append(mesh)
        print("Converted parts to mesh objects at resolution: {:f}".format(resolution))
        log.info("Converted parts to mesh objects at resolution: {:f}".format(resolution))
        return meshes

    def part2meshStandard(self, part, surfDev=0.1, angDev=0.523599, fineRes=False):
        """
        Converts CAD object to mesh object, and adds mesh object to CAD document
        if part is a list of objects, returns a list of meshes.
        If part isn't a list, freecad throws an error.  Use this to determine
        if part is a list of parts or a single object, and handle each case
        correctly.  Returns a list of mesh objects

        This function uses the FreeCAD Standard algorithm, and defines mesh
        by surface and angular deviation.  Default surface deviation is 0.1mm,
        and default angular deviation is 0.523599rad (30deg)
        """
        if fineRes==True:
            print("Running standard mesher with fine resolution (0.01mm and 3deg deviations)")
            surfDev =0.01
            angDev = 0.0523599
        #Check if this is a single file or list and make it a list
        if type(part) != list:
            part = [part]
        meshes = []
        for i in range(len(part)):
            shape = part[i].Shape.copy(False)
            shape.Placement = part[i].getGlobalPlacement()
            print('Meshing part ' + part[i].Label)
            log.info('Meshing part ' + part[i].Label)
            mesh = MeshPart.meshFromShape(Shape=shape,
                                          LinearDeflection=surfDev,
                                          AngularDeflection=angDev,
                                          Relative=False)
            meshes.append(mesh)
        print("Converted parts to mesh objects using Standard algorithm.")
        log.info("Converted parts to mesh objects using Standard algorithm.")
        return meshes


    def writeMesh2file(self, mesh, label, resolution, path='./', fType='stl'):
        """
        Writes a mesh object to STL file named by part number.
        If mesh is a list of mesh objects, then write a separate file for
        each mesh object in the list.  Clobbers if overWriteMask is True

        type defines mesh type / suffix (defaults to .stl file)
        """
        #Check if this is a single file or list and make it a list
        if type(mesh) != list:
            mesh = [mesh]
        if type(label)!= np.ndarray:
            if type(label) != list:
                label = [label]
        if type(resolution) != list:
            resolution=[resolution]*len(mesh)

        #Recursively make dirs for STLs
        print("making STL directory")
        log.info("making STL directory: "+path)
        tools.makeDir(path, clobberFlag=False, mode=self.chmod, UID=self.UID, GID=self.GID)

        for i in range(len(mesh)):
            # ___ (3 underdashes) is the str we use to separate mesh name from resolution
            # this MATTERS when we read back in a mesh (see self.loadROIMesh and self.loadIntersectMesh)

            #standard meshing algorithm
            stdList = ['standard', 'Standard', 'STANDARD']
            if self.BYOM==True:
                filename = path + label[i]
            else:
                if resolution[i] in stdList:
                    filename = path + label[i] + "___"+resolution[i]+"."+fType
                #mefisto meshing algorithm
                else:
                    filename = path + label[i] + "___{:.6f}mm.".format(float(resolution[i]))+fType
            if os.path.exists(filename) and self.overWriteMask == False:
                print("Not clobbering mesh file...")
            else:
                print("Writing mesh file: " + filename)
                log.info("Writing mesh file: " + filename)
                mesh[i].write(filename)
                os.chmod(filename, self.chmod)
                os.chown(filename, self.UID, self.GID)

        print("\nWrote meshes to files")
        log.info("\nWrote meshes to files")
        return

    def loadROIMesh(self, filenames, idx):
        """
        Reads a previously generated STL file and saves object into class.  If
        filename is a list of filenames, then read each into a separate index
        of mesh variable in class.  filename should match a part number from the
        ROI

        BYOM = Bring Your Own Mesh.  This will be set to True when using
        terminal user interface if PFC csv file has an STL instead of
        a part name in the PFCname column

        """
        #Check if this is a single file or list and make it a list
        if type(filenames) == str:
            filenames = [filenames]
        for file in filenames:
            mesh = Mesh.Mesh(file)
            #HEAT generated mesh
            if self.BYOM==False:
                partnum = file.split('/')[-1].split('___')[0]
    #            idx = np.where(np.asarray(self.ROI) == partnum)[0][0]
                #Find CAD object that matches this part number
                for i in range(len(self.CADobjs)):
                    if partnum == self.CADobjs[i].Label:
                        self.ROIparts[idx] = self.CADobjs[i]
            self.ROImeshes[idx] = mesh

        print("Loaded STL files")
        log.info("Loaded STL files")
        return

    def loadIntersectMesh(self, filenames):
        """
        Reads a previously generated STL file and saves object into class.  If
        filename is a list of filenames, then read each into a separate index
        of mesh variable in class.
        """
        #Check if this is a single file or list and make it a list
        if type(filenames) == str:
            filenames = [filenames]
        for file in filenames:
            print('Loading ' + file)
            log.info('Loading ' + file)
            mesh = Mesh.Mesh(file)
            #HEAT generated mesh
            if self.BYOM==False:
                partnum = file.split('/')[-1].split('___')[0]
                idx = np.where(np.asarray(self.intersectList) == partnum)[0][0]
                #Find CAD object that matches this part number
                for i in range(len(self.CADobjs)):
                    if partnum == self.CADobjs[i].Label:
                        self.intersectParts[idx] = self.CADobjs[i]
            #BYOM
            else:
                partnum = file.split('/')[-1]
                idx = np.where(np.asarray(self.intersectList) == partnum)[0][0]
            self.intersectMeshes[idx] = mesh
        print("Loaded Intersection STL files")
        log.info("Loaded Intersection STL files")
        return

    def loadGyroMesh(self, filenames, idx):
        """
        Reads a previously generated STL file and saves object into class.  If
        filename is a list of filenames, then read each into a separate index
        of mesh variable in class.  filename should match a part number from the
        ROI
        """
        #Check if this is a single file or list and make it a list
        if type(filenames) == str:
            filenames = [filenames]
        for file in filenames:
            mesh = Mesh.Mesh(file)
            partnum = file.split('/')[-1].split('___')[0]
#            idx = np.where(np.asarray(self.ROI) == partnum)[0][0]
            #Find CAD object that matches this part number
            for i in range(len(self.CADobjs)):
                if partnum == self.CADobjs[i].Label:
                    self.gyroParts[idx] = self.CADobjs[i]
            self.gyroMeshes[idx] = mesh
        print("Loaded STL files")
        log.info("Loaded STL files")
        return


    def load1Mesh(self, filename):
        """
        Reads a previously generated STL file and generates 1 mesh object.
        """
        mesh = Mesh.Mesh(filename)
        return mesh

    def createEmptyMesh(self):
        """
        returns an empty mesh object
        """
        mesh = Mesh.Mesh()
        return mesh

    def minmaxExtent(self, x,y,z, unitConvert = 1000.0, verbose=False):
        """
        Gets the Rmin, Rmax, Zmin and Zmax of all facets xyz in a mesh to 
        determine the overall extent of the meshed surface. A global set is then updated.
        This is used to generate a bounding box for field line tracing.
        """
        R = np.sqrt(x*x + y*y)
        Rmin = R.min()/unitConvert
        Rmax = R.max()/unitConvert
        Zmin = z.min()/unitConvert
        Zmax = z.max()/unitConvert
        if verbose == True:
            print('Extent of mesh:',Rmin, Rmax, Zmin, Zmax)
        if self.Rmin is None: self.Rmin = Rmin
        elif Rmin < self.Rmin: self.Rmin = Rmin
        
        if self.Rmax is None: self.Rmax = Rmax
        elif Rmax > self.Rmax: self.Rmax = Rmax
        
        if self.Zmin is None: self.Zmin = Zmin
        elif Zmin < self.Zmin: self.Zmin = Zmin
        
        if self.Zmax is None: self.Zmax = Zmax
        elif Zmax > self.Zmax: self.Zmax = Zmax
        return

    def normsCentersAreas(self, meshes, bndybox = False, verbose=False):
        """
        Gets face normals and face centers.  Both norms and centers are arrays
        of length mesh.CountFacets, consisting of three components (x,y,z) per
        facet
        This also updates the global self.Rmin,self.Rmax,self.Zmin,self.Zmax of 
        the bounding box
        """
        #Check if this is a single mesh or list and make it a list
        if type(meshes) != list:
            meshes = [meshes]

        norms = []
        centers = []
        areas = []
        for k,mesh in enumerate(meshes):
            #mesh = obj.Mesh
            if (mesh == None) or (mesh=='None'):
                print("No Mesh for one of these objects.  Did you have a typo in input file?")
                print("Check HEAT output for Mesh Not Found errors")
                log.info("No Mesh for one of these objects.  Did you have a typo in input file?")
                log.info("Check HEAT output for Mesh Not Found errors")
            else:
                N_facets = mesh.CountFacets
                x = np.zeros((N_facets,3))
                y = np.zeros((N_facets,3))
                z = np.zeros((N_facets,3))

                for i,facet in enumerate(mesh.Facets):
                    #mesh points
                    for j in range(3):
                        x[i][j] = facet.Points[j][0]
                        y[i][j] = facet.Points[j][1]
                        z[i][j] = facet.Points[j][2]

                # scale and permute if necessary
                x,y,z = self.scale_and_permute(x,y,z)
                # get face normals and face centers
                norms.append(self.faceNormals(mesh))
                centers.append(self.faceCenters(x,y,z))
                areas.append(self.faceAreas(mesh))
                if bndybox:
                    if verbose == True:
                        print('Part:',self.intersectParts[k].Label)
                    if len(x) > 0:
                        self.minmaxExtent(x,y,z)
        return norms,centers,areas


    def scale_and_permute(self, x_old, y_old, z_old, permute_mask=False, unitConvert=1.0):
        """
        Scales input mesh vectors if necessary (ie for unit conversion)
        Performs coordinate permutation on input mesh vectors if necessary
        (ie if CAD had y-axis as vertical axis)
        """
        if hasattr(self,'permute_mask'):
            permute_mask = self.permute_mask
        if hasattr(self,'unitConvert'):
            unitConvert = self.unitConvert
        if hasattr(self, 'BYOM'):
            if self.BYOM == True:
                permute_mask = False


        #First handle coordinate permutations (preserve right hand rule)
        if permute_mask==True:
            x = z_old
            y = x_old
            z = y_old
        else:
            x = x_old
            y = y_old
            z = z_old
        #Scale inputs to get units in meters
        x *= float(unitConvert)
        y *= float(unitConvert)
        z *= float(unitConvert)
        return x, y, z


    def faceNormals(self, mesh):
        """
        returns normal vectors for single freecad mesh object in cartesian
        coordinates
        """
        #face normals
        normals = []
        for i, facet in enumerate(mesh.Facets):
            vec = np.zeros((3))
            for j in range(3):
                vec[j] = facet.Normal[j]
            normals.append(vec)
        return np.asarray(normals)

    def faceAreas(self, mesh):
        """
        returns face areas for mesh element
        """
        #face area
        areas = []
        for i, facet in enumerate(mesh.Facets):
            areas.append(facet.Area)
        return np.asarray(areas)


    def faceCenters(self, x, y, z):
        """
        returns centers of freecad mesh triangle in cartesian coordinates
        """
        #face centers
        centers = np.zeros((len(x), 3))
        centers[:,0] = np.sum(x,axis=1)/3.0
        centers[:,1] = np.sum(y,axis=1)/3.0
        centers[:,2] = np.sum(z,axis=1)/3.0
        return centers

    def stp2stl(self, resolution = None):
        """
        Reads in an STEP file (ISO 10303-21) and outputs an STL triangular mesh
        with maximum edge length defined by self.gridRes
        """
        if resolution == None: resolution = self.ROIGridRes

        t0 = time.time()
        shape = Part.Shape()
        shape.read(self.STPfile)
        print("CAD STEP read took {:f} seconds".format(time.time() - t0))
        mesh_shp = MeshPart.meshFromShape(shape, MaxLength=resolution)
        print("Part mesh took {:f} seconds".format(time.time() - t0))
        mesh_shp.write(self.STLfile)
        print("STP => STL conversion completed in {:f} seconds".format(time.time() - t0))

        return

    def getCOMs(self, parts):
        """
        Finds center of masses for a list of parts
        """
        #Check if this is a single part or list and make it a list
        if type(parts) != list:
            parts = [parts]

        #Find center of masses (COMs)
        COMs = []
        for part in parts:
            com = part.Shape.CenterOfMass
            COMs.append(com)

        COMs = np.asarray(COMs)
        return COMs

    def findRelativePhi(self, sourceParts, targetParts):
        """
        Finds relative phi between source part and all other parts in CADparts.
        Phi for each part is calculated at the center of mass (COM).  deltaPhis
        is an array with sources in one dimension and targets in other
        dimension, describing the relative angle between sources and targets.
        Source parts are all parts in the ROI.  Target parts are all the parts
        in the input STP file.
        """
        #Check if this is a single part or list and make it a list
        if type(sourceParts) != list:
            sourceParts = [sourceParts]
        if type(targetParts) != list:
            targetParts = [targetParts]

        deltaPhis = np.zeros((len(sourceParts),len(targetParts)))
        for i,source in enumerate(sourceParts):
            sourceCOM = self.getCOMs(source)[0]
            r,z,phi = tools.xyz2cyl(sourceCOM[0],sourceCOM[1],sourceCOM[2])
            for j,target in enumerate(targetParts):
                targetCOM = self.getCOMs(target)[0]
                r_t,z_t,phi_t = tools.xyz2cyl(targetCOM[0],targetCOM[1],targetCOM[2])
#                #Handle cases where we have negative angles
                if phi_t < 0:
                    phi_t = phi_t + 2*np.pi
                deltaPhis[i,j] = phi_t - phi
                if deltaPhis[i,j] > np.pi:
                    deltaPhis[i,j] = deltaPhis[i,j] - 2*np.pi

        return deltaPhis



    def findPotentialIntersectParts(self,deltaPhis,sourceBts,sourceParts,targetParts):
        """
        Uses center of masses (COMs) of the parts in the ROI and the toroidal
        field at each COM to determine which other parts need to be checked
        for intersections.
        intersect_mask is a bitmask (binary) array with sources in one dimension
        and targets in other dimension.  Value is 1 if target is potential
        intersection part and 0 if target is not potential intersection part.
        The toriodal component of magnetic field at source part is the
        parameter used to determine if an intersection is possible.
        """
        #Check if this is a single part or list and make it a list
        if type(sourceParts) != list:
            sourceParts = [sourceParts]
        if type(targetParts) != list:
            targetParts = [targetParts]

        intersect_mask = np.zeros((len(sourceParts),len(targetParts)))

        #Only use tiles who are upstream in toroidal field direction
        for i,source in enumerate(sourceParts):
            if sourceBts[i] > 0:
                intersect_mask[np.where(deltaPhis <= 0)] = 1
            else:
                intersect_mask[np.where(deltaPhis >= 0)] = 1

        #Now eliminate tiles that are over 0.25m from source COM in any direction
        sourceCOMs = self.getCOMs(sourceParts)
        targetCOMs = self.getCOMs(targetParts)
        for i in range(len(sourceCOMs)):
            for j in range(len(targetCOMs)):
                delta = np.abs(np.subtract(sourceCOMs[i],targetCOMs[j]))
                if (delta[0] > 500) or (delta[1] > 500) or (delta[2] > 500):
                     intersect_mask[i,j] = 0
        return intersect_mask

    def meshPotentialIntersects(self, intersect_mask, sourceParts, targetParts,
                                resolution):
        """
        Creates mesh objects for the parts set to 1 in intersect_mask.
        First checks to see if mesh at desired resolution exists.  If mesh
        already exists, loads it, otherwise creates new mesh object.
        """
        #Check if this is a single part or list and make it a list
        if type(sourceParts) != list:
            sourceParts = [sourceParts]
        if type(targetParts) != list:
            targetParts = [targetParts]

        #Make a list of all the target part numbers we need to check
        idx = np.where(intersect_mask == 1)
        parts = []
        labels = []
        for j,target in enumerate(targetParts):
            if intersect_mask[j] == 1:
                parts.append(target)
                labels.append(target.Label)

        parts = list(parts)
        labels = list(labels)
        meshes = self.part2mesh(parts,resolution)
        return meshes, labels

    def stripSTPfile(self,partfile,rawSTP,outfile=None,partsOnly=True):
        """
        Strips an stpfile down to the parts defined in the parts csv input file
        STPfile is the output file defined in input file to HEAT, and is included
        in self variable.  rawSTP is the input CAD file that we want to strip.

        If partsOnly is True then we only copy parts (not assemblies), which
        technically means only objects with type=Part.Feature
        """
        print('Stripping STP file')
        t0 = time.time()
        with open(partfile) as f:
            part_list = f.read().splitlines()
        print("Read parts list...")
        print(part_list)

        #Input / Output STEP files
        infile = rawSTP
        if outfile is None:
            outfile = self.STPfile

        #If a shape has a label in part_list, keep it
        CAD = Import.open(infile)
        newobj = []
        count = 0
        for i,obj in enumerate(FreeCAD.ActiveDocument.Objects):
            if any(substring in obj.Label for substring in part_list):
                #conditional to check if item is part (Part.Feature) or
                # assembly (App.Part).
                # This could be adapted in future to exclude objects containing
                # specific string (like "_ASM") in Label that CAD engineer uses
                # for assemblies
                if partsOnly==True:
                    if type(obj)==Part.Feature:
                        count+=1
                        newobj.append(obj)
                        newobj[-1].Placement = obj.getGlobalPlacement()
                else:
                    count+=1
                    newobj.append(obj)
                    newobj[-1].Placement = obj.getGlobalPlacement()

        #Export to a new step file
        Import.export(newobj, outfile)
        print("Step file export complete.")
        print("Exported {:d} part objects".format(count))
        print("Execution took {:f} seconds".format(time.time() - t0))
        return

    def readIntersects(self, infile, targetParts):
        """
        read intersection parts by partname
        returns bitmask where 1 means that part is a potential intersection and
        0 means there is not potential intersection on that target
        """
        data = pd.read_csv(infile, sep=',', comment='#', names=['Part'], skipinitialspace=True)
        intersect = np.zeros((len(targetParts)))
        for j,target in enumerate(targetParts):
            for name in data['Part']:
                if target.Label == str(name):
                    intersect[j] = 1
        return intersect

    def extrudeFace(self, partName):
        """
        extrude a part object face

        To get subshape:
        >>> shp = obj.Shape
        >>> sub = obj.getSubObject("Face4")
        """
        import Draft
        import BOPTools.JoinFeatures
        for i,part in enumerate(self.CADparts):
            if part.Label == partName:
                vector = FreeCAD.Vector(0,10,0)
                newPart = Draft.extrude(part, vector, solid=True)
                newPart.Label = part.Label + "Extrusion"
                j = BOPTools.JoinFeatures.makeConnect(name= 'Connect')
                print(part)
                print(newPart)
                j.Objects = [part, newPart]
                j.Proxy.execute(j)
                j.purgeTouched()

                #newPart.Placement = part.getGlobalPlacement()
                self.CADparts.append(newPart)
                self.CADobjs.append(newPart)


        return

    def getPolCrossSection(self, rMax, zMax, phi):
        """
        gets a poloidal cross section of the CAD at user defined toroidal angle
        """

        slices = []
        for part in self.CADparts:
            ##method 1 uses vector and double
            #wires = []
            #for wire in part.Shape.slice(FreeCAD.Vector(0,1,0), 4):
            #    wires.append(wire)
            #comp = Part.Compound(wires)
            #name = part.Label + '_cs'
            #slice=self.CADdoc.addObject("Part::Feature",name)
            #slice.Shape=comp
            #slices.append(slice)

            #method 2 uses plane
            plane = self.createPolPlane(rMax,zMax,phi)
            sec = part.Shape.section(plane.Shape)
            obj = self.CADdoc.addObject("Part::Feature", part.Label+"_cs")
            obj.Shape = sec
            self.CADdoc.recompute()
            slices.append(obj)

        return slices

    def createPolPlane(self, rMax, zMax, torAngle):
        """
        creates a poloidal plane

        user defines toroidal angle, maximum r and z
        plane will be 2*zMax in height and rMax in width
        """
        plane = self.CADdoc.addObject("Part::Plane", "HEATplane")
        plane.Length = 2*zMax
        plane.Width = rMax
        planeOrig = FreeCAD.Vector(0, 0, zMax)
        planeRot = FreeCAD.Rotation(-90, 90, -1.0*torAngle)
        plane.Placement = FreeCAD.Placement(planeOrig, planeRot)
        return plane

    def makeComp(self, parts):
        """
        makes a compound from parts
        """
        shps = [p.Shape for p in parts]
        comp = Part.makeCompound(shps)
        obj=self.CADdoc.addObject("Part::Feature","compoundSection")
        obj.Shape = comp
        return obj

    def faceFromEdges(self, edges):
        """
        adds a face to edges that form a contour
        """


        return face

    def checkWireClosed(self, edges):
        """
        checks if edges are closed

        requires list of edges (<Edge object>)
        """
        return Part.Wire(edges).isClosed()

    def createEdge(self, p1, p2):
        """
        creates a wire, or a line, or an edge, from two points

        p1 and p2 should be freecad points (for example, (0,0,0) )
        """
        return Part.makeLine(p1,p2)


    def createWire(self, shape):
        """
        creates a wire from shape obj.  will filter out all parts except
        for edges
        """
        #edges = []
        #for p in shapes:
        #    if type(p)==Part.Edge:
        #        edges.append(p)
        print(len(shape.Edges))
        print(type(shape))
        try:
            w = Part.Wire(shape.Edges)
        except:
            w = None
        return w

    def loadExternalSTL(self, filename):
        """
        import STL mesh
        """
        mesh = Mesh.Mesh(filename)
        print("Loaded STL files")
        log.info("Loaded STL files")
        return mesh


    def getVertexesFromEdges(self, edges, discretize=True, radixFigs=3):
        """
        create an array of XYZ coordinates corresponding to the vertexes in a
        list of FreeCAD edge objects

        edges is list of FreeCAD edge objects

        returns a list of numpy arrays of the X,Y,Z coordinates for each vertex

        note that vertexList is NOT ORDERED.  to weave these coordinate together,
        into a contour, use:   self.findContour(vertexList)

        if discrtetize is true, curves are discretized

        radixFigs is number of figures after the radix point for rounding.
        if you get an error about "contour = np.vstack([contour,contour[0,:]])"
        you may need to change this

        """
        vertexList = []
        for edge in edges:
            x = np.array([])
            y = np.array([])
            z = np.array([])
            #handle curves
            #kif discretize==True:
            if edge.Edges[0].Curve.TypeId != 'Part::GeomLine' and discretize==True:
                N = int(edge.Edges[0].Length / 20.0) #discretize in 20mm segments
                if N < 2:
                    N=2
                #N = 5
                x0 = [v.x for v in edge.Curve.discretize(N)]
                y0 = [v.y for v in edge.Curve.discretize(N)]
                z0 = [v.z for v in edge.Curve.discretize(N)]
                for i in range(N-1):
                    x = np.round([x0[i], x0[i+1]], radixFigs) #round to nearest micron
                    y = np.round([y0[i], y0[i+1]], radixFigs)
                    z = np.round([z0[i], z0[i+1]], radixFigs)
                    vertexList.append(np.vstack([x,y,z]).T)
            #handle lines
            else:
                x = np.hstack([x, np.round([v.X for v in edge.Vertexes], radixFigs) ])
                y = np.hstack([y, np.round([v.Y for v in edge.Vertexes], radixFigs) ])
                z = np.hstack([z, np.round([v.Z for v in edge.Vertexes], radixFigs) ])
                vertexList.append(np.vstack([x,y,z]).T)
        return vertexList




    def findContour(self, edgeList, seedIdx=0):
        """
        weaves a contour together from a list of unordered XYZ vertices.
        each list element corresponds to an edge that was taken from a FreeCAD
        edge object.

        function starts at a seedIdx, and then 'connects the dots' as it 'weaves'
        the contour together by finding edges that share common vertexes

        returns a list of independent contours
        """
        Npts = 0
        allIndexes = np.arange(len(edgeList))
        idxs = [seedIdx]
        contours = []
        #this ugly beast loops through all the edges in the object and weaves
        #together the coordinates of a contour
        while len(idxs) < len(edgeList):

            if len(idxs) > 1:
                leftovers = np.array(list(set(allIndexes)-set(idxs)))
                seedIdx = leftovers[0]

            #the initial vertex that we start from
            vtx = edgeList[seedIdx][-1,:]
            contour = vtx

            #loop thru all the edges looking for that vertex
            for c in range(len(edgeList)):
                for i,edge in enumerate(edgeList):
                    #if we already used this edge, dont use it again
                    if i in idxs:
                        continue
                    else:
                        for j,row in enumerate(edge):
                            #if we found the original vertex in another edge's vertex list
                            if np.all(vtx==row):
                                tmp = np.vstack([edge[:j], edge[j+1:]])
                                contour = np.vstack([contour,tmp])
                                vtx = contour[-1]
                                idxs.append(i)
                                breaker = True
                                break
                            else:
                                breaker=False
                            if breaker == True:
                                break
            #append 1st index to close contour
            if len(contour.shape) < 2:
                print("Curve discretization did not work here.  Try turning off!")
            contour = np.vstack([contour,contour[0,:]])
            contours.append(contour)
        return contours

    def globalMeshTranslation(self, mesh):
        """
        translates a mesh by global xyzT (in [mm]) vector
        """
        noneList = [None, 'None', 'none', 'NA', 'na']
        testx = self.gTx not in noneList
        testy = self.gTy not in noneList
        testz = self.gTz not in noneList

        if np.logical_or(np.logical_or(testx,testy), testz):
            if self.gTx != None:
                xT = float(self.gTx)
            else:
                xT = 0.0
            if self.gTy != None:
                yT = float(self.gTy)
            else:
                yT = 0.0
            if self.gTz != None:
                zT = float(self.gTz)
            else:
                zT = 0.0

            xyzT = np.array([xT,yT,zT])
            mesh.Placement.move(FreeCAD.Vector(xyzT))

            print("Global mesh translation:")
            print('xT = {:f}[mm]'.format(xT))
            print('yT = {:f}[mm]'.format(yT))
            print('zT = {:f}[mm]'.format(zT))
        else:
            print("No global mesh translations defined.")
            log.info("No global mesh translations defined.")
        return mesh


    def repairMeshFreeCAD(self, p:str, stlOut:str, name:str, mesh:object):
        """
        fixes broken meshes using freecad.  saves new mesh in file
        """       
        mesh.fixSelfIntersections()
        mesh.fixDegenerations(0.000000)
        mesh.removeDuplicatedPoints()
        mesh.harmonizeNormals()
        mesh.removeNonManifolds()

        self.writeMesh2file(mesh, name, 'standard', path=p)
        mesh = Mesh.Mesh(p+stlOut)

        return mesh.isSolid()

    def repairMeshOpen3D(self, path:str, stlIn:str, stlOut, part: object, stpName:str):
        """
        an attempt to repair leaky meshes.

        First, tries to repair the mesh by using open3d utilities.
        If that doesn't work, then it 
            1) steps out the individual part object (using freecad) \n
            2) loads the part using gmsh  \n
            3) meshes the part with gmsh  \n
            4) uses open3d to repair any mesh defects  \n
            5) saves repaired mesh  
        
        Future versions of this function could use different libraries

        arguments
        path: string that contains path to stl and where future stl/stp will be saved
        stlIn: name of stl file to read / save
        stlOut: name of stl file to read / save
        part: freecad part object that was originally used to create the leaky mesh
        stpName: name of stp file to save
        
        """
        fIn = path + stlIn
        fOut = path + stlOut
        fOut2 = path + 'repair.ply'
        fStep = path + stpName
        m = o3d.io.read_triangle_mesh(fIn)
        #first test the mesh
        testList = self.checkMeshProperties(m)

        if testList[-2] != True:
            print("Repair attempt 1 using open3D...")
            log.info("Repair attempt 1 using open3D...")
            m = self.open3dRemoveMeshDefects(m)
            testList = self.checkMeshProperties(m)
        
            if testList[-2] == True:
                print("Mesh Repaired...writing")
                log.info("Mesh Repaired...writing")
            
            else:
                #first save an stp file of this part
                print("Mesh repair attempt 1 failed.  Trying another method")
                log.info("Mesh repair attempt 1 failed.  Trying another method")

            #legacy code sort of works.  leave for ideas
            #    print("Writing STP file for new mesh generation...")
            #    log.info("Writing STP file for new mesh generation...")
            #    os.remove(fOut)
            #    self.saveSTEP(fStep, [part])
            #    now mesh using gmsh
            #    import gmsh
            #    gmsh.initialize()
            #    gmsh.model.occ.importShapes(fStep)
            #    gmsh.model.occ.synchronize()
            #    gmsh.model.mesh.generate(3)
            #    gmsh.write(fOut)
            #    gmsh.finalize()
            #    m = o3d.io.read_triangle_mesh(fOut)
            #    m = self.open3dRemoveMeshDefects(m)
            #    testList = self.checkMeshProperties(m)
            #    if testList[-2] == True:
            #        print("Mesh repaired during attempt 2.")
            #        log.info("Mesh repaired during attempt 2.")
            #    else:
            #        print("WARNING: could not repair mesh")
            #        log.info("WARNING: could not repair mesh")

        #regardless of repair state, write mesh file
        os.remove(fOut)
        o3d.io.write_triangle_mesh(fOut, m)
        m = o3d.io.read_triangle_mesh(fOut)
        testList = self.checkMeshProperties(m)

        return testList[-2]


    def open3dRemoveMeshDefects(self, m:object):
        """
        removes mesh defects using open3d

        m is an open3d mesh object
        returns updated mesh object
        """
        m.remove_degenerate_triangles()
        m.remove_duplicated_triangles()
        m.remove_duplicated_vertices()
        m.remove_non_manifold_edges()
        m.compute_triangle_normals()
        m.compute_vertex_normals()
        return m


    def checkMeshProperties(self, mesh:object, visualize=False):
        """
        checks mesh properties of an open3D mesh object

        mesh must be an open3d object
        if visualize is true, renders a visualization of the object
        with defects colored
        """
        mesh.compute_vertex_normals()
        edge_manifold = mesh.is_edge_manifold(allow_boundary_edges=True)
        edge_manifold_boundary = mesh.is_edge_manifold(allow_boundary_edges=False)
        vertex_manifold = mesh.is_vertex_manifold()
        self_intersecting = mesh.is_self_intersecting()
        watertight = mesh.is_watertight()
        orientable = mesh.is_orientable()
        print(f"  edge_manifold:          {edge_manifold}")
        print(f"  edge_manifold_boundary: {edge_manifold_boundary}")
        print(f"  vertex_manifold:        {vertex_manifold}")
        print(f"  self_intersecting:      {self_intersecting}")
        print(f"  watertight:             {watertight}")
        print(f"  orientable:             {orientable}")

        testList = [edge_manifold, edge_manifold_boundary,
                    vertex_manifold, self_intersecting,
                    watertight, orientable]

        if visualize == True:
            geoms = [mesh]
            if not edge_manifold:
                edges = mesh.get_non_manifold_edges(allow_boundary_edges=True)
                geoms.append(self.edges_to_lineset(mesh, edges, (1, 0, 0)))
            if not edge_manifold_boundary:
                edges = mesh.get_non_manifold_edges(allow_boundary_edges=False)
                geoms.append(self.edges_to_lineset(mesh, edges, (0, 1, 0)))
            if not vertex_manifold:
                verts = np.asarray(mesh.get_non_manifold_vertices())
                pcl = o3d.geometry.PointCloud(
                    points=o3d.utility.Vector3dVector(np.asarray(mesh.vertices)[verts]))
                pcl.paint_uniform_color((1, 0, 1))
                geoms.append(pcl)
            if self_intersecting:
                intersecting_triangles = np.asarray(
                    mesh.get_self_intersecting_triangles())
                intersecting_triangles = intersecting_triangles[0:1]
                intersecting_triangles = np.unique(intersecting_triangles)
                print("  # visualize self-intersecting triangles")
                triangles = np.asarray(mesh.triangles)[intersecting_triangles]
                edges = [
                    np.vstack((triangles[:, i], triangles[:, j]))
                    for i, j in [(0, 1), (1, 2), (2, 0)]
                ]
                edges = np.hstack(edges).T
                edges = o3d.utility.Vector2iVector(edges)
                geoms.append(self.edges_to_lineset(mesh, edges, (1, 0, 1)))
            o3d.visualization.draw_geometries(geoms, mesh_show_back_face=True)
        return testList

    def edges_to_lineset(self, mesh, edges, color):
        """
        creates lineset from list of edges

        taken from open3d tutorials: open3d_tutorial.py
        """

        ls = o3d.geometry.LineSet()
        ls.points = mesh.vertices
        ls.lines = edges
        colors = np.empty((np.asarray(edges).shape[0], 3))
        colors[:] = color
        ls.colors = o3d.utility.Vector3dVector(colors)
        return ls
    
    def createFEMmeshNetgen(self, obj, MaxSize=1000, Fineness="Moderate",
                          Optimize = True, SecondOrder=True, name='FEMMeshNetgen'):
        """
        Creates a FEM mesh object using the netgen mesher.  User specifies
        the size and fineness of the mesh.  Uses freecad api to netgen

        Some of the functionality in this function may not work depending on the 
        freecad version.  older versions do not have netgen module.
        also requires an environment with netgen installed (from apt repo)

        """
        print("Generating Mesh Obj")
        doc = self.CADdoc
        mesh = doc.addObject('Fem::FemMeshShapeNetgenObject', name)
        mesh.Shape = obj
        mesh.MaxSize = MaxSize
        mesh.Fineness = Fineness
        mesh.Optimize = Optimize
        mesh.SecondOrder = SecondOrder
        doc.recompute()
        
        if hasattr(self, 'FEMmeshes'):
            if self.FEMmeshes is None:
                self.FEMmeshes = [mesh]
            else:
                self.FEMmeshes.append(mesh)
        else:
            self.FEMmeshes = [mesh]
        return mesh


    def createFEMmeshGmsh(self, obj, minLength=0, maxLength=0, name='FEMMeshGmsh'):
        """
        Creates a FEM mesh object using the Gmsh mesher.  User specifies
        the minimum / maximum length of the mesh elements, which defaults 
        to 0 (auto).  Uses freecad api to gmsh

        Some of the functionality in this function may not work depending on the 
        freecad version.  older versions do not have ObjectsFem module.
        also requires an environment with gmsh installed (from apt repo)
        """
        import ObjectsFem
        print("Generating Mesh Obj")
        doc = self.CADdoc
        mesh = ObjectsFem.makeMeshGmsh(doc, name + "_Mesh")
        mesh.Label = name
        mesh.Part = obj
        #mesh.ElementDimension = "From Shape"
        mesh.CharacteristicLengthMin = minLength
        mesh.CharacteristicLengthMax = maxLength
        #mesh.SecondOrderLinear = True
        #mesh.ElementOrder = 2  # Set to 2 for second order elements   

        #optimizations that prevent degenerate mesh elements
        mesh.MeshSizeFromCurvature = 12
        mesh.Recombine3DAll = True
        mesh.RecombinationAlgorithm = "Simple"
        mesh.OptimizeNetgen = True
        doc.recompute()

        from femmesh.gmshtools import GmshTools as gt
        gmsh_mesh = gt(mesh)

        error = None
        try:
            error = gmsh_mesh.create_mesh()
        except:
            print("Could not create 3D mesh...")
            print(error)
            print("Do you have the python-is-python3 package installed?")
            log.info("Could not create 3D mesh...")
            log.info(error)
            log.info("Do you have the python-is-python3 package installed?")
        
        if hasattr(self, 'FEMmeshes'):
            if self.FEMmeshes is None:
                self.FEMmeshes = [mesh]
            else:
                self.FEMmeshes.append(mesh)
        else:
            self.FEMmeshes = [mesh]

        return mesh
    
    def importFEMmesh(self, file):
        """
        imports FEM mesh and returns FEM mesh object
        """
        print(file)
        mesh = Fem.open(file)
        self.CADdoc = FreeCAD.ActiveDocument
        self.FEMmeshes = self.CADdoc.Objects
        return

    def exportFEMmesh(self, mesh, file):
        """
        exports FEM mesh
        """
        print(file)
        if type(mesh) != 'list':
            mesh = [mesh]
        Fem.export(mesh, file)
        return