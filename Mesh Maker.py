#Author-Casey Rogers
#Description-Converts a triangular mesh into printable assemblable triangles




'''
'''

import adsk.core, adsk.fusion, traceback
import math
import os

handlers = []

""" Represents the different types of hinges. An openEdge hinge is used on
    an edge in an open surface with no adjacent triangle on the given side.
    IE, a side with no hinge at all. """
class hingeType:
    male = "male"
    female = "female"
    openEdge = "openEdge"

""" The browser names of the various important comonents in the template triangle.
    For example, "fStr1" represents the female hinge component on side one of the triangle.
    Change these values if you modify the browser names. """
fStr1 = "F1:1"
fStr2 = "F1:2"
fStr3 = "F1:3"
mStr1 = "M1:1"
mStr2 = "M1:2"
mStr3 = "M1:3"
bStr1 = "binaryBits:1"
bStr2 = "binaryBits:2"
bStr3 = "binaryBits:3"
cs = "frame"
coreStr = "center"
templateStr = "Mesh Maker Template"
fStr1l, fStr1r, fStr2l, fStr2r, fStr3l, fStr3r = "1l", "1r", "2l", "2r", "3l", "3r"

"""design = app.activeProduct
rootComp = design.rootComponent;"""
app = adsk.core.Application.get()
ui  = app.userInterface
templateDesign = None
templateComp = None
meshDesign = None
meshComp = None


""" This adds buttons to the toolbar panel and creates the input box, among
    other things. """
def run(context):
    try:

        #event handlers
        class mmCommandCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
            def __init__(self):
                super().__init__()
            def notify(self, args):
                cmd = args.command
                inputs = cmd.commandInputs

                selInput0 = inputs.addSelectionInput('mesh', 'Object to be printed', 'Select a body containing only tris to be printed')
                selInput0.addSelectionFilter('Bodies')
                selInput0.setSelectionLimits(1,1)

                inputs.addStringValueInput('dir', 'Export directory', "C:/example/<mesh_name>")

                inputs.addBoolValueInput('validate', 'Color bad triangles', True)
                inputs.addBoolValueInput('debug', 'Debugging Mode', True)
                inputs.addBoolValueInput('report', 'Report sides', True)
                inputs.addBoolValueInput('preview', 'Preview assembly', True)

                initialVal = adsk.core.ValueInput.createByReal(0)
                inputs.addValueInput('testNum', 'Number of Triangles to Test', 'cm', initialVal)

                # Handles core bodies, feature currently not supported
                """for body in rootComp.bRepBodies:
                    if body.name[0:len(coreStr)] == coreStr:
                        selInput = inputs.addSelectionInput(body.name, 'Faces with alternate center \'%s\'' % body.name, 'Select faces to receive alternate center')
                        selInput.addSelectionFilter("Faces")
                        selInput.setSelectionLimits(0, 0)"""


                # Connect up to command related events.
                onExecute = CommandExecutedHandler()
                cmd.execute.add(onExecute)
                handlers.append(onExecute)


        class CommandExecutedHandler(adsk.core.CommandEventHandler):
            def __init__(self):
                super().__init__()
            def notify(self, args):
                app = adsk.core.Application.get()
                ui  = app.userInterface
                try:
                    command = args.firingEvent.sender

                    # Get the data and settings from the command inputs.
                    coreDict = {}
                    for input in command.commandInputs:
                        if input.id == 'mesh':
                            mesh = input.selection(0).entity
                        if input.id == 'validate':
                            validate = input.value
                        if input.id == 'debug':
                            debug = input.value
                        if input.id == 'report':
                            report = input.value
                        if input.id == 'preview':
                            preview = input.value
                        if input.id == 'dir':
                            saveDir = input.value
                            print(saveDir)
                        if input.id == 'testNum':
                            testNum = input.value
                        if input.id[0:len(coreStr)] == coreStr:
                            tmp = []
                            for i in range(input.selectionCount):
                                tmp.append(input.selection(i).entity)
                            coreDict[input.id] = tmp

                    makeMesh(mesh, validate, debug, report, preview, saveDir, testNum, coreDict)
                    # Do something with the results.
                except:
                    if ui:
                        ui.messageBox('command executed failed:\n{}'.format(traceback.format_exc()))

        #add add-in to UI
        cmdDefs = ui.commandDefinitions
        mmButton = cmdDefs.addButtonDefinition('mmBtn', 'MeshMaker', 'Converts a mesh into printable triangles')

        mmCreated = mmCommandCreatedEventHandler()
        mmButton.commandCreated.add(mmCreated)
        handlers.append(mmCreated)

        createPanel = ui.allToolbarPanels.itemById('SolidCreatePanel')

        buttonControl = createPanel.controls.addCommand(mmButton, 'mmBtn')

        # Make the button available in the panel.
        buttonControl.isPromotedByDefault = True
        buttonControl.isPromoted = True

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

""" Stop the add-in. """
def stop(context):
    try:
        cmdDef = ui.commandDefinitions.itemById('mmBtn')
        if cmdDef:
            cmdDef.deleteMe()
        createPanel = ui.allToolbarPanels.itemById('SolidCreatePanel')
        cntrl = createPanel.controls.itemById('mmBtn')
        if cntrl:
            cntrl.deleteMe()

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

""" Execute the add-in given the supplied inputs. """
def makeMesh(mesh, validateColor, debug, report, preview, saveDir, testNum, coreDict):
    # Find the design files and root components
    global app
    global ui
    global templateDesign
    global templateComp
    global meshDesign
    global meshComp
    app = adsk.core.Application.get()
    ui  = app.userInterface
    meshDesign = app.activeProduct
    meshComp = meshDesign.rootComponent
    docs = app.documents
    
    templateDoc = None
    for i in range(docs.count):
        doc = docs.item(i)
        if doc.name[0:len(templateStr)] == templateStr:
            templateDoc = doc
    if not templateDoc:
        ui.messageBox('Could not find "' + templateStr + '". Open the file\
        and re-run')
        return
    templateDesign = templateDoc.products.itemByProductType("DesignProductType")
    if not templateDesign:
        ui.messageBox('No active Fusion design', 'No Design')
        return
    templateComp = templateDesign.rootComponent
    
    # Find hinge, frame and center bodies
    occs = templateComp.occurrences
    bodies = templateComp.bRepBodies
    # Find the Hinge components and center body
    f1 = occs.itemByName(fStr1)
    f2 = occs.itemByName(fStr2)
    f3 = occs.itemByName(fStr3)

    m1 = occs.itemByName(mStr1)
    m2 = occs.itemByName(mStr2)
    m3 = occs.itemByName(mStr3)

    b1 = occs.itemByName(bStr1)
    b2 = occs.itemByName(bStr2)
    b3 = occs.itemByName(bStr3)

    center = templateComp.bRepBodies.itemByName("frame")

    if not f1:
        ui.messageBox("Side 1 female hinge (Component '" + fStr1 + "') not found")
        return
    if not f2:
        ui.messageBox("Side 2 female hinge (Component '" + fStr2 + "') not found")
        return
    if not f3:
        ui.messageBox("Side 3 female hinge (Component '" + fStr3 + "') not found")
        return
    if not m1:
        ui.messageBox("Side 1 male hinge (Component '" + mStr1 + "') not found")
        return
    if not m2:
        ui.messageBox("Side 2 male hinge (Component '" + mStr2 + "') not found")
        return
    if not m3:
        ui.messageBox("Side 3 male hinge (Component '" + mStr3 + "') not found")
        return
    if not center:
        ui.messageBox("Center (Body '" + cs + "' not found")
        return
    if not (b1 and b2 and b3):
        ui.messageBox("Missing binary bit pattern (" + bStr1 +", " + bStr2 + ", " + bStr3 + ")")
        return

    # Find the hinge bodies
    f1l = bodies.itemByName(fStr1l)
    f1r = bodies.itemByName(fStr1r)
    f2l = bodies.itemByName(fStr2l)
    f2r = bodies.itemByName(fStr2r)
    f3l = bodies.itemByName(fStr3l)
    f3r = bodies.itemByName(fStr3r)
    if not (f1l and f1r and f2l and f2r and f3l and f3r):
        ui.messageBox("A female hinge body wasn't found (" + fStr1l +", " + fStr1r + ", " + fStr2l + "...)")
        return

    # Find the side parameters
    paramList = templateDesign.userParameters
    s1 = paramList.itemByName("sideOne")
    s2 = paramList.itemByName("sideTwo")
    s3 = paramList.itemByName("sideThree")
    digits = paramList.itemByName("binaryDigits")
    if not s1:
        ui.messageBox("Parameter 'sideOne' not found")
        return
    if not s2:
        ui.messageBox("Parameter 'sideTwo' not found")
        return
    if not s3:
        ui.messageBox("Parameter 'sideThree' not found")
        return
    if not digits:
        ui.messageBox("Parameter 'binaryDigits' not found")
        return
    digits = digits.value
    uniqueEdges = mesh.edges.count
    exp = 1
    while (2**exp < uniqueEdges):
        exp += 1
    if exp > digits:
        ui.messageBox("Not enough binary digits, need at least %r digits to represent %.0f unique edges" %
        (exp, uniqueEdges))
        return

    def hingeBodies(side1, sideNum):
        returnBodies = []
        if sideNum == 1:
            fBodyl = f1l
            fBodyr = f1r
            fOcc = f1
            mOcc = m1
        elif sideNum == 2:
            fBodyl = f2l
            fBodyr = f2r
            fOcc = f2
            mOcc = m2
        else:
            fBodyl = f3l
            fBodyr = f3r
            fOcc = f3
            mOcc = m3

        mComp = mOcc.component
        fComp = fOcc.component

        if side1.hinge == hingeType.male:
            for body in mComp.bRepBodies:
                proxy = proxyBody(mComp.bRepBodies, mOcc, body.name)
                returnBodies.append(proxy)
        elif side1.hinge == hingeType.female:
            for body in fComp.bRepBodies:
                proxy = proxyBody(fComp.bRepBodies, fOcc, body.name)
                returnBodies.append(proxy)
            returnBodies.append(fBodyl)
            returnBodies.append(fBodyr)
        core = bodies.itemByName(coreStr)
        if core:
            returnBodies.append(core)
        return returnBodies

    def coreBodies(face):
        for core in coreDict:
            if face in coreDict[core]:
                return bodies.itemByName(core)
        return None

    def update(side1, side2, side3):
            try:
                if isinstance(side1, float):
                    s1.expression = "%.3f mm" % side1
                    s2.expression = "%.3f mm" % side2
                    s3.expression = "%.3f mm" % side3
                else:
                    #s1.expression = "%.3f mm" % ((side1.length + s1.value*10)/2.0)
                    #s2.expression = "%.3f mm" % ((side2.length + s2.value*10)/2.0)
                    #s3.expression = "%.3f mm" % ((side3.length + s3.value*10)/2.0)
                    s1.expression = "%.3f mm" % side1.length
                    s2.expression = "%.3f mm" % side2.length
                    s3.expression = "%.3f mm" % side3.length
            except:
                # Triangle Failed
                yn = ui.messageBox("Triangle Failed!\n s1: %d, %.3f, %r\ns2: %d, %.3f, %r\ns3: %d, %.3f, %r" % (
                side1.index, side1.length, side1.hinge, side2.index, side2.length, side2.hinge,
                side3.index, side3.length, side3.hinge), "Triangle Error", 1)
                if yn != 0:
                    return True




    """ Process a single triangle with the specified behavior (debug, report sides). """
    def process():

        # Assign the largest length to s1, improves reliability and solves a vertical s2/s3 glitch
        if (sideTup[1].length > sideTup[0].length and sideTup[1].length > sideTup[2].length):
            side1, side2, side3 = sideTup[1], sideTup[2], sideTup[0]
        elif (sideTup[2].length > sideTup[0].length and sideTup[2].length > sideTup[1].length):
            side1, side2, side3 = sideTup[2], sideTup[0], sideTup[1]
        else:
            side1, side2, side3 = sideTup[0], sideTup[1], sideTup[2]


        validate(face, side1.length, side2.length, side3.length, validateColor)
        if not debug:
            if update(side1, side2, side3):
                return True
            export(side1, side2, side3, face)
            #update(250.0, 250.0, 250.0)
        if report:
            ui.messageBox("s1: %d, %.3f, %r\ns2: %d, %.3f, %r\ns3: %d, %.3f, %r" % (
            side1.index, side1.length, side1.hinge, side2.index, side2.length, side2.hinge,
            side3.index, side3.length, side3.hinge))

    """ Export a triangle with the given sides. This involves combining
        the proper hinges to the frame body and then exporting the frame body. """
    def export(side1, side2, side3, face):

        exportMgr = templateDesign.exportManager
        importMgr = app.importManager
        fileName = "\\%s_%i_%i_%i__%.3f_%.3f_%.3f" % (
        mesh.parentComponent.name, side1.index, side2.index, side3.index,
        side1.length, side2.length, side3.length)

        """ Place the triangle being assembled on the main assembly. """
        def preview():
            tempComp = combine.bodies.item(0).parentComponent

            exportOptions = exportMgr.createSATExportOptions(saveDir + fileName + ".sat", tempComp)
            exportMgr.execute(exportOptions)
            importOptions = importMgr.createSATImportOptions(saveDir + fileName + ".sat")
            importMgr.importToTarget(importOptions, meshComp)

            occ = findOccByName(fileName[1:] + ":1", meshComp)
            if occ:
                body = occ.component.bRepBodies.item(0)
                body = body.createForAssemblyContext(occ)
            move(body, face)

        def move(body, face):
            # Create a collection of entities for move
            moveBody = adsk.core.ObjectCollection.create()
            moveBody.add(body)

            # Create a transform to do move
            transform = adsk.core.Matrix3D.create()
            inputs = originInputs() + faceInputs(face, side1, side2, side3)
            transform.setToAlignCoordinateSystems(*inputs)

            # Create a move feature
            moveFeats = meshComp.features.moveFeatures
            moveFeatureInput = moveFeats.createInput(moveBody, transform)
            moveFeats.add(moveFeatureInput)

        combineBodies = []
        combineBodies.extend(binaryBodies(side1, b1, digits))
        combineBodies.extend(binaryBodies(side2, b2, digits))
        combineBodies.extend(binaryBodies(side3, b3, digits))


        combineBodies.extend(hingeBodies(side1, 1))
        combineBodies.extend(hingeBodies(side2, 2))
        combineBodies.extend(hingeBodies(side3, 3))

        core = coreBodies(face)
        if core:
            combineBodies.append(core)

        combines = templateComp.features.combineFeatures

        bodyCollection = adsk.core.ObjectCollection.create()
        for bod in combineBodies:
            bodyCollection.add(bod)
        combInput = combines.createInput(center, bodyCollection)
        combInput.isNewComponent = True
        combine = combines.add(combInput)


        exportOptions = exportMgr.createSTLExportOptions(center, saveDir + fileName + ".stl")
        exportMgr.execute(exportOptions)

        if preview:
            preview()

        """tempComp = combine.bodies.item(0).parentComponent
        occs = tempComp.allOccurrences
        ui.messageBox(str(occs.count))
        for i in range(occs.count):
            occs.item(i).deleteMe()"""
        combine.deleteMe()
            

        timeline = templateDesign.timeline
        tempFeature = timeline.item(timeline.markerPosition - 1).entity
        tempFeature.deleteMe()

        os.remove(saveDir + fileName + ".sat")


        adsk.doEvents()
        #app.activeViewport.refresh()

    yn = ui.messageBox("There are %r total faces with %.0f unique edges" % (
    mesh.faces.count, uniqueEdges), "Mesh Maker", 1)
    if yn != 0:
        return True
    # Iterate through the Mesh and export the stls
    # TEST handles the "num triangles to test" input
    sideIter = meshIter(mesh)
    try:
        i = 0
        test = False
        if testNum > 0:
            test = True
        while not test or testNum > 0:
            temp = sideIter.next()
            if not temp:
                return
            sideTup = temp[0]
            face = temp[1]
            cancel = process()
            if cancel:
                ui.messageBox("Canceled with error")
                return
            i += 1
            testNum -= 1
    except StopIteration:
        return


""" Given a single side, return the bodies necessary to create its binary bit
    pattern and its proper concavity indicator. """
def binaryBodies(side, bitOcc, totalDigits):
    digits = side.index.bit_length()
    binary = str(bin(side.index))[2:]
    returnBodies = []
    offset = (totalDigits - digits) // 2

    bodies = bitOcc.component.bRepBodies

    leftTopcc = proxyBody(bodies, bitOcc, "lConcavet")
    rightTopcc = proxyBody(bodies, bitOcc, "rConcavet")
    leftBotcc = proxyBody(bodies, bitOcc, "lConcaveb")
    rightBotcc = proxyBody(bodies, bitOcc, "rConcaveb")

    if not (leftTopcc and rightTopcc and leftBotcc and rightBotcc):
        return

    topBits = []
    botBits = []
    i = 1
    while (i <= totalDigits):
        topBit = proxyBody(bodies, bitOcc, "%rt" % i)
        if not topBit:
            ui.messageBox("Missing bit named '%rt'" % i)
            return
        topBits.append(topBit)

        botBit = proxyBody(bodies, bitOcc, "%rb" % i)
        if not botBit:
            ui.messageBox("Missing bit named '%rt'" % i)
            return
        botBits.append(botBit)
        i += 1

    if side.hinge == hingeType.female:
        topBits = list(reversed(topBits))
        botBits = list(reversed(botBits))
        returnBodies.append(leftBotcc)
        if side.convex:
            returnBodies.append(rightTopcc)
            returnBodies.append(rightBotcc)
    else:
        returnBodies.append(rightBotcc)
        if side.convex:
            returnBodies.append(leftTopcc)
            returnBodies.append(leftBotcc)


    #ui.messageBox("binary: %r    totalDigits: %s    Digits: %s  Offset: %s" % (binary, totalDigits, digits, offset))
    for i in range(int(totalDigits)):
        #ui.messageBox("i - offset: %i" % (i - int(offset)))
        if digits % 2 == 1:
            strIndex = i - int(offset)
            #ui.messageBox("strIndex: %r    binary: %r" % (strIndex, binary))
        else:
            strIndex = i - int(offset) - 1
            #ui.messageBox("strIndex: %r    binary: %r" % (strIndex, binary))
        if i < offset or i >= totalDigits - offset:
            returnBodies.append(botBits[i])
        #ui.messageBox("binary: %r    index: %i" % (binary, i - int(offset)))
        elif not strIndex < 0 and binary[strIndex] == '1':
            returnBodies.append(botBits[i])
            returnBodies.append(topBits[i])
    return returnBodies

""" Given the name of a body, its parent occurence and the bodies within
    the occurence's component, return the body's proxy. """
def proxyBody(compBodies, occ, name):
    body = compBodies.itemByName(name)

    if not body:
        ui.messageBox('Component body named "%s" not found' % name)
        return

    return body.createForAssemblyContext(occ)

""" A basic class describing the side of a triangle. """
class Side:
    def __init__(self, index, length, hinge, convex):
        self.index = index
        self.length = length
        self.hinge = hinge
        self.convex = convex

""" Return True if the edge represents a convex hinge, return false otherwise.
    Code provided by Brian Ekins. """
def convex(edge):
    if openEdge(edge):
        return False
    try:
        # Get the two faces connected by the edge and get the normal of each face.
        face1 = edge.faces.item(0)
        face2 = edge.faces.item(1)
        ret = face1.evaluator.getNormalAtPoint(face1.pointOnFace)
        normal1 = ret[1]
        ret = face2.evaluator.getNormalAtPoint(face2.pointOnFace)
        normal2 = ret[1]

        # Get the co-edge of the selected edge for face1.
        if edge.coEdges.item(0).loop.face == face1:
            coEdge = edge.coEdges.item(0)
        elif edge.coEdges.item(1).loop.face == face1:
            coEdge = edge.coEdges.item(1)

        # Create a vector that represents the direction of the co-edge.
        if coEdge.isOpposedToEdge:
            edgeDir = edge.startVertex.geometry.vectorTo(edge.endVertex.geometry)
        else:
            edgeDir = edge.endVertex.geometry.vectorTo(edge.startVertex.geometry)

        # Get the cross product of the face normals.
        cross = normal1.crossProduct(normal2)

        # Check to see if the cross product is in the same or opposite direction
        # of the co-edge direction.  If it's opposed then it's a convex angle.
        if edgeDir.angleTo(cross) > math.pi/2:
            return True
        else:
            return False
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

""" An iterator that iterates through a given bRep object, returns a list
    containing three Side objects for each triangular face in the bRep object. """
class meshIter:

    def __init__(self, mesh):
        self.mesh = mesh

        self.faces = mesh.faces
        self.f = 0
        self.fCount = self.faces.count

        self.visitedEdges = []
    def __iter__(self):
        return self
    def next(self):
        while (self.f < self.fCount):
            face = self.faces.item(self.f)
            edges = face.edges
            eCount = edges.count
            if eCount > 3:
                ui.messageBox("Non-triangular face found")
                return False
            rv = []
            e = 0
            while (e < eCount):
                edge = edges.item(e)
                length = brepLength(edge)
                try:
                    edgeNum = self.visitedEdges.index(edge)
                    if (edgeNum % 2 == 0):
                        hinge = hingeType.female
                    else:
                        hinge = hingeType.male
                except ValueError:
                    edgeNum = len(self.visitedEdges)
                    self.visitedEdges.append(edge)
                    if openEdge(edge):
                        hinge = hingeType.openEdge
                    elif (edgeNum % 2 == 0):
                        hinge = hingeType.male
                    else:
                        hinge = hingeType.female
                rv.append(Side(edgeNum, length, hinge, convex(edge)))
                e += 1

            self.f += 1
            return rv, face
        raise StopIteration()

""" Confirm that a triangle has valid values, if not, color invalid triangle
    red and ask if the user wishes to cancel. """
def validate(face, s1, s2, s3, color):
    try:
        paramList = templateDesign.userParameters

        minAlt = paramList.itemByName("minAltitude")
        if not minAlt:
            ui.messageBox("Parameter 'minAltitude' not found")


        libs = app.materialLibraries
        lib = libs.itemByName("Fusion 360 Appearance Library")
        #for lib in libs:
        #    ui.messageBox(str(lib.name))
        if not lib:
            ui.messageBox("Material library 'Fusion 360 Appearance Library' not found")
        apps = lib.appearances


        apps = templateDesign.appearances
        badAlt = apps.itemByName("Short Altitude")
        badSide = apps.itemByName("Short Side")
        if not badAlt or not badSide:
            ui.messageBox("Appearance 'Short Altitude' or appearance 'Short Side' not found")
        if not minAlt:
            ui.messageBox("Parameter 'minAltitude' not found")


        # Scary formula for calculating the smallest altitude of a triangle give three sides, where s1 is largest
        altitude = ((2*(s1**2)*(s2**2) + 2*(s2**2)*(s3**2) + 2*(s1**2)*(s3**2) - s3**4 - s2**4 - s1**4)**.5) / (2*s1)

        minAlt = minAlt.value * 10

        if s2 < 20 or s3 < 20:
            if color:
                face.appearance = badSide
        elif altitude < minAlt:
            if color:
                face.appearance = badAlt
    except:
            ui.messageBox('Validate Failed:\n{}'.format(traceback.format_exc()))


""" Return the length of the given linear edge in MM. Return value is a double. """
def brepLength(edge):
    return edge.startVertex.geometry.distanceTo(edge.endVertex.geometry) * 10

""" Return True if the given edge is associated with only a single face. IE
    it borders a hole in a mesh and should not be given a hinge. """
def openEdge(edge):
    if edge.faces.count == 1:
        return True
    return False

def originInputs():
    paramList = templateDesign.userParameters
    thick = paramList.itemByName("thickness")
    if not thick:
        ui.messageBox("Parameter 'thickness' not found")
    thick = thick.value/2.0
    lst = []
    # fromOrigin
    lst.append(adsk.core.Point3D.create(0.0, 0.0, thick))
    # fromX
    lst.append(adsk.core.Vector3D.create(1.0, 0.0, 0.0))
    # fromY
    lst.append(adsk.core.Vector3D.create(0.0, -1.0, 0.0))
    # fromZ
    lst.append(adsk.core.Vector3D.create(0.0, 0.0, -1.0))
    return lst

def faceInputs(face, side1, side2, side3):
    edges = face.edges
    edge1, edge2 = None, None
    for i in range(edges.count):
        edge = edges.item(i)
        length = edgeLength(edge)
        if length == side1.length:
            edge1 = edge
        elif length == side2.length:
            edge2 = edge
    if not edge1 or not edge2:
        ui.messageBox("faceInputs: Edges don't match")
    point = findSharedPoint(edge1, edge2)
    if not point:
        ui.messageBox("faceInputs: Could not find a shared point")

    lst = []
    # toOrigin
    lst.append(point)
    # toX
    vX = edgeToVector(edge1, point)
    vX.scaleBy(1.0/vX.length)
    # toZ
    success, vZ = face.evaluator.getNormalAtPoint(face.pointOnFace)
    if not success:
        ui.messageBox("faceInputs: Couldn't find normal")
    vZ.scaleBy(1.0/vZ.length)
    # toY
    vY = vZ.crossProduct(vX)
    vY.scaleBy(1.0/vY.length)
    lst.append(vX)
    lst.append(vY)
    lst.append(vZ)
    message = []
    for v in lst[1:]:
        message.append(v.length)
    return lst

def findOccByName(name, rootComp):
    compList = rootComp.allOccurrences
    for i in range(compList.count):
        comp = compList.item(i)
        if comp.name == name:
            return comp
    ui.messageBox("findCompByName: Could not find a component named %s" % name)
    return None

def edgeLength(edge):
    return 10*edge.startVertex.geometry.distanceTo(edge.endVertex.geometry)

# Returns a point3D object A where A is shared between the two input edges
def findSharedPoint(edge0, edge1):
    point0_0 = edge0.startVertex
    point0_1 = edge0.endVertex
    point1_0 = edge1.startVertex
    point1_1 = edge1.endVertex
    if (point0_0 == point1_0) or (point0_0 == point1_1):
        pointA = point0_0
    elif (point0_1 == point1_0) or (point0_1 == point1_1):
        pointA = point0_1
    else:
        return False
    return pointA.geometry

# Returns a vector aligned with the given edge starting at the given point
def edgeToVector(edge, point):
    p1, p2 = edge.startVertex.geometry, edge.endVertex.geometry
    if point.isEqualTo(p1):
        return point.vectorTo(p2)
    elif point.isEqualTo(p2):
        return point.vectorTo(p1)
    else:
        ui.messageBox("edgeToVector: point isn't on edge")