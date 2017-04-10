import os
import imp
import sys
import time
import shutil
import random
import string
import subprocess
import collections

import numpy as np
import sitkUtils as su
import SimpleITK as sitk
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *


LINEAR = vtk.vtkTransformInterpolator.INTERPOLATION_TYPE_LINEAR
SPLINE = vtk.vtkTransformInterpolator.INTERPOLATION_TYPE_SPLINE

interpolationMap = {'Linear': LINEAR, 'Spline': SPLINE}


class Animation(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Animation"
        self.parent.categories = ["Utilities"]
        self.parent.dependencies = []
        self.parent.contributors = ["Fernando Perez-Garcia (fepegar@gmail.com - Institute of the Brain and Spine - Paris)"]
        self.parent.helpText = """
        """
        self.parent.acknowledgementText = """
        """



class AnimationWidget(ScriptedLoadableModuleWidget):

    def __init__(self, parent):

        ScriptedLoadableModuleWidget.__init__(self, parent)


    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = AnimationLogic()
        self.selectors = []
        firstSelector = self.logic.getSelector(self)
        self.selectors.append(firstSelector)

        tranformNodeName = 'Animation transform node'
        self.transformNode = slicer.util.getNode(tranformNodeName)
        if self.transformNode is None:
            self.transformNode = slicer.vtkMRMLTransformNode()
            self.transformNode.SetName(tranformNodeName)
            self.transformNode.SetScene(slicer.mrmlScene)
        slicer.mrmlScene.AddNode(self.transformNode)

        self.makeGUI()


    def makeGUI(self):
        self.transformableGroupBox = qt.QGroupBox('Choose a transformable node')
        self.transformableGroupBox.setLayout(qt.QVBoxLayout())
        self.layout.addWidget(self.transformableGroupBox)
        self.transformableNodeSelector = slicer.qMRMLNodeComboBox()
        self.transformableNodeSelector.nodeTypes = ["vtkMRMLTransformableNode"]
        self.transformableNodeSelector.selectNodeUponCreation = True
        self.transformableNodeSelector.addEnabled = False
        self.transformableNodeSelector.removeEnabled = True
        self.transformableNodeSelector.noneEnabled = False
        self.transformableNodeSelector.showHidden = False
        self.transformableNodeSelector.setMRMLScene(slicer.mrmlScene)
        self.transformableGroupBox.layout().addWidget(self.transformableNodeSelector)


        self.transformsGroupBox = qt.QGroupBox('Transforms')
        self.transformsLayout = qt.QVBoxLayout(self.transformsGroupBox)
        self.selectorsLayout = qt.QVBoxLayout()
        self.selectorsLayout.addLayout(self.selectors[0].boxLayout)
        self.transformsLayout.addLayout(self.selectorsLayout)
        self.layout.addWidget(self.transformsGroupBox)


        self.addTransformPushButton = qt.QPushButton('Add')
        self.addTransformPushButton.clicked.connect(self.onAddTransformSelector)
        self.addTransformPushButton.setStyleSheet('color: rgb(0, 150, 0)')
        self.transformsLayout.addWidget(self.addTransformPushButton)


        self.parametersGroupBox = qt.QGroupBox('Additional parameters')
        self.parametersLayout = qt.QFormLayout(self.parametersGroupBox)
        self.layout.addWidget(self.parametersGroupBox)

        self.numberOfStepsSpinBox = qt.QSpinBox()
        self.numberOfStepsSpinBox.setMinimum(1)
        self.numberOfStepsSpinBox.setMaximum(1000)
        self.numberOfStepsSpinBox.value = 100
        self.parametersLayout.addRow('Number of steps: ', self.numberOfStepsSpinBox)

        radioButtonsGroupBox = qt.QGroupBox()
        radioButtonsLayout = qt.QHBoxLayout(radioButtonsGroupBox)

        self.interpolationRadioButtons = []
        for interpType in interpolationMap:
            radioButton = qt.QRadioButton(interpType)
            self.interpolationRadioButtons.append(radioButton)
            radioButtonsLayout.addWidget(radioButton)
            if interpolationMap[interpType] == LINEAR:
                radioButton.setChecked(True)
        self.parametersLayout.addRow('Interpolation type: ', radioButtonsGroupBox)


        self.runButton = qt.QPushButton('Run')
        self.runButton.clicked.connect(self.onRun)
        self.layout.addWidget(self.runButton)

        self.layout.addStretch(0)


    def onAddTransformSelector(self):
        selector = self.logic.getSelector(self)
        self.selectorsLayout.addLayout(selector.boxLayout)
        self.selectors.append(selector)


    def onRun(self):
        transforms = []
        for selector in self.selectors:
            transformNode = selector.currentNode()
            if transformNode is None:
                continue
            matrix = transformNode.GetMatrixTransformToParent()
            transform = vtk.vtkTransform()
            transform.SetMatrix(matrix)
            transforms.append(transform)
        transformableNode = self.transformableNodeSelector.currentNode()
        for button in self.interpolationRadioButtons:
            if button.isChecked():
                interpolationType = interpolationMap[str(button.text)]
        self.logic.runAnimation(transformableNode,
                                transforms,
                                self.transformNode,
                                numSteps=self.numberOfStepsSpinBox.value,
                                interpolationType=interpolationType)



class AnimationLogic(ScriptedLoadableModuleLogic):

    def getSelector(self, moduleWidget, basename='Transform'):
        return TransformSelector(moduleWidget, basename)


    def runAnimation(self, transformableNode, transforms, transformNode, numSteps=100, interpolationType=LINEAR):
        # Go from the identity if only one transform is received
        if len(transforms) == 1:
            transforms.insert(0, vtk.vtkTransform())

        slicer.mrmlScene.AddNode(transformNode)
        transformableNode.SetAndObserveTransformNodeID(transformNode.GetID())

        interpolator = vtk.vtkTransformInterpolator()
        interpolator.SetInterpolationType(interpolationType)

        for t, transform in enumerate(transforms):
            # t = float(i) / len(transforms)
            interpolator.AddTransform(t, transform)

        lm = slicer.app.layoutManager()
        view = lm.threeDWidget(0).threeDView()

        times = np.linspace(interpolator.GetMinimumT(),
                            interpolator.GetMaximumT() - 0.001,  # hack
                            numSteps)

        auxTransform = vtk.vtkTransform()
        for t in times:
            interpolator.InterpolateTransform(t, auxTransform)
            vtkMatrix = auxTransform.GetMatrix()
            print vtkMatrix
            transformNode.SetAndObserveMatrixTransformToParent(vtkMatrix)
            view.forceRender()



class AnimationTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear(0)
        import SampleData
        sampleDataLogic = SampleData.SampleDataLogic()
        self.transformableNode = sampleDataLogic.downloadMRHead()

        # Show in 2D
        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActiveVolumeID(self.transformableNode.GetID())
        slicer.app.applicationLogic().PropagateVolumeSelection(1)

        # And 3D
        volumeRenderingWidgetRep = slicer.modules.volumerendering.widgetRepresentation()
        volumeRenderingWidgetRep.setMRMLVolumeNode(self.transformableNode)
        volumeRenderingNode = slicer.mrmlScene.GetFirstNodeByName('VolumeRendering')
        volumeRenderingNode.SetVisibility(1)

        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()

        self.transform0 = vtk.vtkTransform()

        self.transform1 = vtk.vtkTransform()
        self.transform1.RotateZ(45)
        self.transform1.RotateX(25)
        self.transform1.Translate(20, -100, 30)

        self.transform2 = vtk.vtkTransform()
        self.transform2.RotateZ(-25)
        self.transform2.RotateX(-30)
        self.transform2.Translate(-20, -30, -30)

        self.transform3 = vtk.vtkTransform()
        self.transform3.Translate(0, -300, 0)

        self.transform4 = vtk.vtkTransform()

        self.transforms = [self.transform0,
                           self.transform1,
                           self.transform2,
                           self.transform3,
                           self.transform4]
        for i, t in enumerate(self.transforms):
            # print i, t
            t.Update()

        tranformNodeName = 'Animation test transform node'
        self.transformNode = slicer.util.getNode(tranformNodeName)
        if self.transformNode is None:
            self.transformNode = slicer.vtkMRMLTransformNode()
            self.transformNode.SetName(tranformNodeName)
            self.transformNode.SetScene(slicer.mrmlScene)
        slicer.mrmlScene.AddNode(self.transformNode)

        self.numberOfSteps = 100

        self.logic = AnimationLogic()


    def runTest(self):
        """Run as few or as many tests as needed here.
        """

        self.test_1_linear()
        self.test_1_spline()
        self.test_all_linear()
        self.test_all_spline()


    def test_1_linear(self):
        self.setUp()
        name = 'Testing linear interpolation, one transform'
        self.delayDisplay(name)
        transforms = [self.transforms[1]]
        self.logic.runAnimation(self.transformableNode,
                                transforms,
                                self.transformNode,
                                numSteps=self.numberOfSteps,
                                interpolationType=LINEAR)
        self.delayDisplay('%s completed successfully' % name)


    def test_1_spline(self):
        self.setUp()
        name = 'Testing spline interpolation, one transform'
        self.delayDisplay(name)
        transforms = [self.transforms[1]]
        self.logic.runAnimation(self.transformableNode,
                                transforms,
                                self.transformNode,
                                numSteps=self.numberOfSteps,
                                interpolationType=SPLINE)
        self.delayDisplay('%s completed successfully' % name)


    def test_all_linear(self):
        self.setUp()
        name = 'Testing linear interpolation, all transforms'
        self.delayDisplay(name)
        transforms = self.transforms
        self.logic.runAnimation(self.transformableNode,
                                transforms,
                                self.transformNode,
                                numSteps=self.numberOfSteps * 2,
                                interpolationType=LINEAR)
        self.delayDisplay('%s completed successfully' % name)


    def test_all_spline(self):
        self.setUp()
        name = 'Testing spline interpolation, all transforms'
        self.delayDisplay(name)
        transforms = self.transforms
        self.logic.runAnimation(self.transformableNode,
                                transforms,
                                self.transformNode,
                                numSteps=self.numberOfSteps * 2,
                                interpolationType=SPLINE)
        self.delayDisplay('%s completed successfully' % name)



class TransformSelector(slicer.qMRMLNodeComboBox):

    def __init__(self, moduleWidget, basename):
        super(TransformSelector, self).__init__()
        self.moduleWidget = moduleWidget

        self.nodeTypes = ["vtkMRMLTransformNode"]
        self.selectNodeUponCreation = True
        self.addEnabled = True
        self.removeEnabled = True
        self.noneEnabled = False
        self.showHidden = False
        # self.showChildNodeTypes = False
        self.setMRMLScene(slicer.mrmlScene)
        self.baseName = basename

        self.removePushButton = qt.QPushButton('Remove')
        self.removePushButton.clicked.connect(self.remove)
        self.removePushButton.setStyleSheet('color: rgb(255, 0, 0)')

        self.boxLayout = qt.QHBoxLayout()
        self.boxLayout.addWidget(self)
        self.boxLayout.addWidget(self.removePushButton)


    def remove(self):
        self.hide()
        self.removePushButton.hide()
        self.moduleWidget.selectors.remove(self)
        del self
