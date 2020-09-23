# '''
# Created on Feb 28, 2017
#
# @author: winfriedw
# '''
#  ################################################################################################
#  #
#  # Code for testing
#  #
# ################################################################################################
# # def z_relative_move(self, zOffset):
# # zStart = self.Zen.Devices.Focus.ActualPosition
# # zEndCalc = zStart + zOffset
# # self.Zen.Devices.Focus.MoveTo(zEndCalc)
# # zEnd = self.Zen.Devices.Focus.ActualPosition
# # print "z_relative_move(" + str(zOffset) + "): zStart=" + str(zStart) + ", zEndCalc=" + str(zEndCalc) + ", zEnd=" + str(zEnd)
# # return zEnd
# #
# #
# # def Z_Down(self):
# # z = self.z_relative_move(-5000)
# # return z
# #
# #
# # def Z_Up(self):
# # z = self.z_relative_move(5000)
# # return z
# #
# #
# # def test(self):
# '''Put test code in here.
# '''
# # Example - Diagonal Stage Moves.czmac
# # v0.1  2016-11-17  JSM
#
# print "--------------------------------------------------"
# print "Macro Start: 'Example - Diagonal Stage Moves'"
#
#
#
# #--- The currently active experiment must be set correctly to acquire images ---
# exp = self.Zen.Acquisition.Experiments.ActiveExperiment
#
# if(exp == None):
#     self.Zen.Application.Pause("Plesae click on the ZEN 'Acquisition' tab, and then run the macro again.")
#     print "There is no active experiment"
# else:
#     #--- Read and capture 1st position (1a) ---
#     imgLive = self.Zen.Acquisition.StartLive_2(exp)
#     self.Zen.Application.Pause("Manually move to position 1 of 2")
#     x1= self.Zen.Devices.Stage.ActualPositionX
#     y1= self.Zen.Devices.Stage.ActualPositionY
#     z1= self.Zen.Devices.Focus.ActualPosition
#     self.Zen.Acquisition.StopLive_2(exp)
#     #imgLive.Close()
#     img1a = self.Zen.Acquisition.AcquireImage_3(exp)
#     self.Zen.Application.Documents.Add(img1a)
# #             img1a.Name = "1a"
#     print "1a: x=" + str(x1) + "; y=" + str(y1) + "; z=" + str(z1)
#
#     #--- Read and capture 2nd position (2a) ---
#     imgLive = self.Zen.Acquisition.StartLive_2(exp)
#     self.Zen.Application.Pause("Manually move to position 2 of 2")
#     x2= self.Zen.Devices.Stage.ActualPositionX
#     y2= self.Zen.Devices.Stage.ActualPositionY
#     z2= self.Zen.Devices.Focus.ActualPosition
#     self.Zen.Acquisition.StopLive_2(exp)
#     #imgLive.Close()
#     img2a = self.Zen.Acquisition.AcquireImage_3(exp)
#     self.Zen.Application.Documents.Add(img2a)
# #             img2a.Name = "2a"
#     print "2a: x=" + str(x2) + "; y=" + str(y2) + "; z=" + str(z2)
#
#     #--- Return to 1st position and capture (1b) ---
#     self.Z_Down()
#     self.Zen.Devices.Stage.MoveTo(x1, y1)
#     self.Z_Up()
#     self.Zen.Devices.Focus.MoveTo(z1)
#     x= self.Zen.Devices.Stage.ActualPositionX
#     y= self.Zen.Devices.Stage.ActualPositionY
#     z= self.Zen.Devices.Focus.ActualPosition
#     img1b = self.Zen.Acquisition.AcquireImage_3(exp)
#     self.Zen.Application.Documents.Add(img1b)
# #             img1b.Name = "1b"
#     print "1b: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
#
#     #--- Return to 2nd position and capture (2b) ---
#     self.Z_Down()
#     self.Zen.Devices.Stage.MoveTo(x2, y2)
#     self.Z_Up()
#     self.Zen.Devices.Focus.MoveTo(z2)
#     x= self.Zen.Devices.Stage.ActualPositionX
#     y= self.Zen.Devices.Stage.ActualPositionY
#     z= self.Zen.Devices.Focus.ActualPosition
#     img2b = self.Zen.Acquisition.AcquireImage_3(exp)
#     self.Zen.Application.Documents.Add(img2b)
# #             img2b.Name = "2b"
#     print "2b: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
#
#     #--- Return to 1st position and capture (1c) ---
#     self.Z_Down()
#     self.Zen.Devices.Stage.MoveTo(x1, y1)
#     self.Z_Up()
#     self.Zen.Devices.Focus.MoveTo(z1)
#     x= self.Zen.Devices.Stage.ActualPositionX
#     y= self.Zen.Devices.Stage.ActualPositionY
#     z= self.Zen.Devices.Focus.ActualPosition
#     img1c = self.Zen.Acquisition.AcquireImage_3(exp)
#     self.Zen.Application.Documents.Add(img1c)
# #             img1c.Name = "1c"
#     print "1c: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
#
#     for i in range(0, 10):
#         print "i=" + str(i)
#
#         #--- Return to 2nd position and capture (2b) ---
#         self.Z_Down()
#         self.Zen.Devices.Stage.MoveTo(x2, y2)
#         self.Z_Up()
#         self.Zen.Devices.Focus.MoveTo(z2)
#         x= self.Zen.Devices.Stage.ActualPositionX
#         y= self.Zen.Devices.Stage.ActualPositionY
#         z= self.Zen.Devices.Focus.ActualPosition
#         img2 = self.Zen.Acquisition.AcquireImage_3(exp)
#         self.Zen.Application.Documents.Add(img2)
# #                 img2.Name = "2"
#         print "2: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
#
#         #--- Return to 1st position and capture (1c) ---
#         self.Z_Down()
#         self.Zen.Devices.Stage.MoveTo(x1, y1)
#         self.Z_Up()
#         self.Zen.Devices.Focus.MoveTo(z1)
#         x= self.Zen.Devices.Stage.ActualPositionX
#         y= self.Zen.Devices.Stage.ActualPositionY
#         z= self.Zen.Devices.Focus.ActualPosition
#         img1 = self.Zen.Acquisition.AcquireImage_3(exp)
#         self.Zen.Application.Documents.Add(img1)
# #                 img1c.Name = "1"
#         print "1: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
#
#
# print "Macro End: 'Example - Diagonal Stage Moves'"
# print "--------------------------------------------------"
