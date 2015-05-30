#Author-Casey Rogers
#Description-Converts a triangular mesh into printable assemblable triangles
'''
'''

import adsk.core, adsk.fusion, traceback
import math

handlers = []

class hingeType:
    male = "male"
    female = "female"
    openEdge = "openEdge"
    
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
fStr1l, fStr1r, fStr2l, fStr2r, fStr3l, fStr3r = "1l", "1r", "2l", "2r", "3l", "3r"

app = adsk.core.Application.get()
ui  = app.userInterface

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

                inputs.addBoolValueInput('debug', 'Debugging Mode', True)
                inputs.addBoolValueInput('report', 'Report sides', True)

                initialVal = adsk.core.ValueInput.createByReal(0)
                inputs.addValueInput('testNum', 'Number of Triangles to Test', 'cm', initialVal)

        
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
                    for input in command.commandInputs:
                        if input.id == 'mesh':
                            mesh = input.selection(0).entity
                        if input.id == 'debug':
                            debug = input.value
                        if input.id == 'report':
                            report = input.value
                        if input.id == 'dir':
                            saveDir = input.value
                            print(saveDir)
                        if input.id == 'testNum':
                            testNum = input.value
                    makeMesh(mesh, debug, report, saveDir, testNum)
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
            

def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        
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

def makeMesh(mesh, debug, report, saveDir, testNum):
    # Find hinge, frame and center bodies
    app = adsk.core.Application.get();
    ui = app.userInterface;
    design = app.activeProduct
    if not design:
        ui.messageBox('No active Fusion design', 'No Design')
        return
    
    rootComp = design.rootComponent;
    if not rootComp:
        return
    occs = rootComp.occurrences
    bodies = rootComp.bRepBodies
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

    center = rootComp.bRepBodies.itemByName("frame")

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
    paramList = design.userParameters
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
        return returnBodies
            
    
    def process():
        
        # Assign the largest length to s1, improves reliability and solves a vertical s2/s3 glitch
        if (sideTup[1].length > sideTup[0].length and sideTup[1].length > sideTup[2].length):
            side1, side2, side3 = sideTup[1], sideTup[2], sideTup[0]
        elif (sideTup[2].length > sideTup[0].length and sideTup[2].length > sideTup[1].length):
            side1, side2, side3 = sideTup[2], sideTup[0], sideTup[1]
        else:
            side1, side2, side3 = sideTup[0], sideTup[1], sideTup[2]
            

        if not debug:
            try:
                s1.expression = "%.3f mm" % side1.length
            except:
                # Attempt to recover by setting next side
                pass

            try:
                s2.expression = "%.3f mm" % side2.length
            except:
                # Attempt to recover by setting next side
                pass

            try:
                s3.expression = "%.3f mm" % side3.length
            except:
                # Triangle Failed
                yn = ui.messageBox("Triangle Failed!\n s1: %d, %.3f, %r\ns2: %d, %.3f, %r\ns3: %d, %.3f, %r" % (
                side1.index, side1.length, side1.hinge, side2.index, side2.length, side2.hinge,
                side3.index, side3.length, side3.hinge), "Triangle Error", 1)
                if yn != 0:
                    return
            export(side1, side2, side3)
        if report:
            ui.messageBox("s1: %d, %.3f, %r\ns2: %d, %.3f, %r\ns3: %d, %.3f, %r" % (
            side1.index, side1.length, side1.hinge, side2.index, side2.length, side2.hinge,
            side3.index, side3.length, side3.hinge))
            """minSide = 10000
            maxSide = 0
            minSide = min(s1Val, s2Val, s3Val, minSide)
            maxSide = max(s1Val, s2Val, s3Val, maxSide)
            ui.messageBox("Min: %.2f\nMax: %.2f" % (minSide, maxSide))"""
        
    def export(side1, side2, side3):
        
        exportMgr = design.exportManager
        fileName = "\\%s_%i_%i_%i__%.3f_%.3f_%.3f.stl" % (
        mesh.parentComponent.name, side1.index, side2.index, side3.index,
        side1.length, side2.length, side3.length)

        combineBodies = []
        combineBodies.extend(binaryBodies(side1, b1, digits))
        combineBodies.extend(binaryBodies(side2, b2, digits))
        combineBodies.extend(binaryBodies(side3, b3, digits))
        
        
        combineBodies.extend(hingeBodies(side1, 1))
        combineBodies.extend(hingeBodies(side2, 2))
        combineBodies.extend(hingeBodies(side3, 3))

        combines = rootComp.features.combineFeatures
        
        bodyCollection = adsk.core.ObjectCollection.create()
        for bod in combineBodies:
            bodyCollection.add(bod)
        combInput = combines.createInput(center, bodyCollection)
        combine = combines.add(combInput)

        exportOptions = exportMgr.createSTLExportOptions(center, saveDir + fileName)
        exportMgr.execute(exportOptions)
        
        combine.deleteMe()

    yn = ui.messageBox("There are %r total faces with %.0f unique edges" % (
    mesh.faces.count, uniqueEdges), "Mesh Maker", 1)
    if yn != 0:
        return True
    # Iterate through the Mesh and export the stls
    sideIter = meshIter(mesh)
    try:
        i = 0
        test = False
        if testNum > 0:
            test = True
        while not test or testNum > 0:
            sideTup = sideIter.next()
            cancel = process()
            if cancel:
                ui.messageBox("Canceled with error")
                return
            i += 1
            testNum -= 1
    except StopIteration:
        return



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
        ui.messageBox("Concavity body not found: 'lConcavet, rConcavet, lConcaveb or rConcaveb'")

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
        else:
            strIndex = i - int(offset) - 1
        if i < offset or i >= totalDigits - offset:
            returnBodies.append(botBits[i])
            #ui.messageBox("topBit: False  i: %i" % i)
        elif not strIndex < 0 and binary[strIndex] == '1':
            #ui.messageBox("binary: %r    index: %i" % (binary, i - int(offset)))
            returnBodies.append(botBits[i])
            returnBodies.append(topBits[i])
    return returnBodies


def proxyBody(compBodies, occ, name):
    body = compBodies.itemByName(name)
    
    return body.createForAssemblyContext(occ)  
    
class Side:
    def __init__(self, index, length, hinge, convex):
        self.index = index
        self.length = length
        self.hinge = hinge
        self.convex = convex

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
            return rv
        raise StopIteration()
    

def brepLength(edge):
    return edge.startVertex.geometry.distanceTo(edge.endVertex.geometry) * 10
    
def openEdge(edge):
    if edge.faces.count == 1:
        return True
    return False
    


#Explicitly call the run function.
#stop({'IsApplicationStartup':True})
#run({'IsApplicationStartup':True})
#stop({'IsApplicationStartup':True})