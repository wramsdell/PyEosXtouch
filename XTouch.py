import pygame.midi
import time
import threading

FAST_TIMER_PERIOD=0.01
SLOW_TIMER_PERIOD=0.1

class ExternalDeviceNotFound(IOError): pass

class XtouchControl(object):
    def __init__(self,channel,midiIn,midiOut,debugMode=False):
        self.channel=channel
        self.midiIn=midiIn
        self.midiOut=midiOut
        self.debug=debugMode
        self.sayName()

    def sayName(self):
        if self.debug: print(self.name)

class Knob(XtouchControl):
    def __init__(self,channel,midiIn,midiOut,pressAndHoldDuration,doublePressDuration,boundHandlers,vTable=[20,1000],debugMode=False):
        self.name="Knob %d"%channel
        self.val=0
        self.boundHandlers=boundHandlers
        self.pressAndHoldDuration=pressAndHoldDuration
        self.doublePressDuration=doublePressDuration
        self.channel=channel
        self.t=threading.Timer(self.pressAndHoldDuration,self.pressAndHoldHandler)
        self.lastPress=0
        self.lastRotationTime=time.time()
        self.vTable=vTable
        XtouchControl.__init__(self,channel,midiIn,midiOut,debugMode)


    def pressHandler(self):
        if self.debug: print("Knob %d pressed"%self.channel)
        self.t=threading.Timer(self.pressAndHoldDuration,self.pressAndHoldHandler)
        self.t.start()
        if "KnobPress" in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            self.boundHandlers[self.channel]["KnobPress"](retval)

    def releaseHandler(self):
        if self.debug: print("Knob %d released"%self.channel)
        self.t.cancel()
        if (time.time()-self.lastPress)<self.doublePressDuration:
            self.lastPress=0    #prevent multiple calls to double-press handler if somebody's button-happy
            self.doublePressHandler()
        else:
            self.lastPress=time.time()
        if "KnobRelease" in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            self.boundHandlers[self.channel]["KnobRelease"](retval)

    def incrementHandler(self,magnitude):
        self.val+=magnitude
        if self.debug: print("Knob %d increment, new value %d"%(self.channel,self.val))
        self.t.cancel()
        deltaT=time.time()-self.lastRotationTime
        if deltaT==0: deltaT=.001
        self.lastRotationTime=time.time()
        velocity=magnitude/deltaT
        speedRange=1
        for i in range(len(self.vTable)):
            if velocity>self.vTable[i]: speedRange=i+2
        if "KnobIncrement" in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            retval["value"]=self.val
            retval["magnitude"]=magnitude
            retval["velocity"]=velocity
            retval["speedRange"]=speedRange
            self.boundHandlers[self.channel]["KnobIncrement"](retval)

    def decrementHandler(self,magnitude):
        self.val-=magnitude
        if self.debug: print("Knob %d decrement, new value %d"%(self.channel,self.val))
        self.t.cancel()
        deltaT=time.time()-self.lastRotationTime
        if deltaT==0: deltaT=.001
        self.lastRotationTime=time.time()
        velocity=magnitude/deltaT
        speedRange=1
        for i in range(len(self.vTable)):
            if velocity>self.vTable[i]: speedRange=i+2
        if "KnobDecrement" in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            retval["value"]=self.val
            retval["magnitude"]=magnitude
            retval["velocity"]=velocity
            retval["speedRange"]=speedRange
            self.boundHandlers[self.channel]["KnobDecrement"](retval)

    def pressAndHoldHandler(self):
        if self.debug: print("Knob %d press and hold"%self.channel)
        if "KnobPressAndHold" in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            self.boundHandlers[self.channel]["KnobPressAndHold"](retval)

    def doublePressHandler(self):
        if self.debug: print("Knob %d double press"%self.channel)
        if "KnobDoublePress" in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            self.boundHandlers[self.channel]["KnobDoublePress"](retval)

class KnobRing(XtouchControl):
    def __init__(self,channel,midiIn,midiOut,debugMode=False):
        self.channel=channel
        self.name="Knob Ring %d"%channel
        XtouchControl.__init__(self,channel,midiIn,midiOut,debugMode)

    def set(self,val):
        self.midiOut.write_short(0xb0,0x30+self.channel,val)

class ScribbleStripLine(XtouchControl):
    def __init__(self,channel,midiIn,midiOut,lineNumber,debugMode=False):
        self.channel=channel
        self.lineNumber=lineNumber
        self.name="Scribble Strip %d Line %d"%(channel,lineNumber)
        XtouchControl.__init__(self,channel,midiIn,midiOut,debugMode)
        self.text=""
        self.blinkState=0
        self.blinkPeriod=0

    def update(self):
        a=[0xf0,0x00,0x00,0x66,0x15,0x12]
        a.append(self.channel*7+(self.lineNumber*56))     #Write the line, starting at index 0+7*channel; when i=1, write the second line starting at 56+7*channel
        for i in range(7):                  #The text field is 7 characters long
            if i<len(self.text):
                ch=self.text[i]      
            else:
                ch=" "                      #Pad any remaining characters with spaces
            a.append(ord(ch))
        a.append(0xf7)
        self.midiOut.write_sys_ex(0,a)

    def blankDisplay(self):                     #Blanks the display but does not delete the stored strings, used by blink.
            a=[0xf0,0x00,0x00,0x66,0x15,0x12]
            a.append(self.channel*7+(self.lineNumber*56))     #When i=0, write the first line, starting at index 0+7*channel; when i=1, write the second line starting at 56+7*channel
            for j in range(7):                  #The text field is 7 characters long
                a.append(ord(" "))
            a.append(0xf7)
            self.midiOut.write_sys_ex(0,a)

    def setText(self,text):
        self.text=text
        self.update()

    def blink(self,blinkState):
        if blinkState>0:
            self.update()
        else:
            self.blankDisplay()

class Button(XtouchControl):
    def __init__(self,channel,midiIn,midiOut,number,pressAndHoldDuration,doublePressDuration,boundHandlers,debugMode=False):
        self.number=number
        self.boundHandlers=boundHandlers
        self.channel=channel
        self.pressAndHoldDuration=pressAndHoldDuration
        self.doublePressDuration=doublePressDuration
        self.name="Button %d number %d"%(channel,number)
        XtouchControl.__init__(self,channel,midiIn,midiOut,debugMode)
        self.led=ButtonLed(self.channel,midiIn,midiOut,self.number)
        self.lastPress=0

    def pressHandler(self):
        if self.debug: print("Button channel {} number {} pressed".format(self.channel,self.number))
#        print("Button channel {} number {} pressed".format(self.channel,self.number))
        self.t=threading.Timer(self.pressAndHoldDuration,self.pressAndHoldHandler)
        self.t.start()
        if "ButtonPress{}".format(self.number) in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            retval["number"]=self.number
            self.boundHandlers[self.channel]["ButtonPress{}".format(self.number)](retval)

    def releaseHandler(self):
        if self.debug: print("Button channel {} number {} released".format(self.channel,self.number))
        self.t.cancel()
        if (time.time()-self.lastPress)<self.doublePressDuration:
            self.lastPress=0    #prevent multiple calls to double-press handler if somebody's button-happy
            self.doublePressHandler()
        else:
            self.lastPress=time.time()
        if "ButtonRelease{}".format(self.number) in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            retval["number"]=self.number
            self.boundHandlers[self.channel]["ButtonRelease{}".format(self.number)](retval)

    def pressAndHoldHandler(self):
        if self.debug: print("Button channel {} number {} press and hold".format(self.channel,self.number))
        if "ButtonPressAndHold{}".format(self.number) in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            retval["number"]=self.number
            self.boundHandlers[self.channel]["ButtonPressAndHold{}".format(self.number)](retval)

    def doublePressHandler(self):
        if self.debug: print("Button channel {} number {} double press".format(self.channel,self.number))
        if "ButtonDoublePress{}".format(self.number) in self.boundHandlers[self.channel]:
            retval={}
            retval["obj"]=self
            retval["channel"]=self.channel
            retval["number"]=self.number
            self.boundHandlers[self.channel]["ButtonDoublePress{}".format(self.number)](retval)

class ButtonLed(XtouchControl):
    def __init__(self,channel,midiIn,midiOut,number,debugMode=False):
        self.number=number
        self.channel=channel
        self.name="Button LED %d number %d"%(channel,number)
        XtouchControl.__init__(self,channel,midiIn,midiOut,debugMode)

    def blink(self,blinkState):
        ledNumber=self.channel+(8*self.number)
        if blinkState>0:
            self.midiOut.write_short(0x90,ledNumber,0x7f)    
        else:
            self.midiOut.write_short(0x90,ledNumber,0x00)    

class VuBar(XtouchControl):
    def __init__(self,channel,midiIn,midiOut,serviceInterval=.1,debugMode=False):
        self.channel=channel
        self.serviceInterval=serviceInterval
        self.name="VU Bar %d"%channel
        self.t=None
        self.val=0
        XtouchControl.__init__(self,channel,midiIn,midiOut,debugMode)

    def set(self,val):
        self.val=val
        if self.val!=0:
            self.midiOut.write_short(0xd0,16*self.channel+self.val,0x00)
            self.t=threading.Timer(self.serviceInterval,self.timerService)
            self.t.start()
        else:
            self.t.cancel()

    def timerService(self):
        self.midiOut.write_short(0xd0,16*self.channel+self.val,0x00)
        self.t=threading.Timer(self.serviceInterval,self.timerService)
        self.t.start()

class Fader(XtouchControl):
    def __init__(self,channel,midiIn,midiOut,debugMode=False):
        self.channel=channel
        self.name="Fader %d"%channel
        XtouchControl.__init__(self,channel,midiIn,midiOut,debugMode)

class Channel(object):
    def __init__(self,channel,midiIn,midiOut,pressAndHoldDuration,doublePressDuration,boundHandlers,debugMode=False):
        self.debug=debugMode
        self.boundHandlers=boundHandlers
        self.channelNumber=channel
        self.knob=Knob(channel,midiIn,midiOut,pressAndHoldDuration,doublePressDuration,boundHandlers,debugMode=debugMode)
        self.knobRing=KnobRing(channel,midiIn,midiOut,debugMode=debugMode)
        self.scribbleStrip=[ScribbleStripLine(channel,midiIn,midiOut,0),ScribbleStripLine(channel,midiIn,midiOut,1)]
        self.button=[]
        for i in range(4):
            self.button.append(Button(channel,midiIn,midiOut,i,pressAndHoldDuration,doublePressDuration,boundHandlers,debugMode))
        self.vuBar=VuBar(channel,midiIn,midiOut)
        self.fader=Fader(channel,midiIn,midiOut)

class XTouch(object):
    def __init__(self,pressAndHoldDuration=1,doublePressDuration=.5,debugMode=False):
        self.debug=debugMode
        self.midiOut=None
        self.midiIn=None
        self.boundHandlers=[{} for sub in range(8)]
        self.blinkTable={}
        self.blinkStep=0
        pygame.midi.init()
        deviceCount=pygame.midi.get_count()
        for i in range(deviceCount):
            if self.debug: print(pygame.midi.get_device_info(i))
            if self.debug: print(pygame.midi.get_device_info(i)[2])
            if pygame.midi.get_device_info(i)[1].decode("utf8")=="X-Touch-Ext":
                if (pygame.midi.get_device_info(i)[2]==1):
                    if self.debug: print("X-Touch Extender input found at device %d"%i)
                    if pygame.midi.get_device_info(i)[4]==0: self.midiIn = pygame.midi.Input(i)
                    else: raise ExternalDeviceNotFound('X-Touch Extender input device busy.')
                elif (pygame.midi.get_device_info(i)[3]==1):
                    if self.debug: print("X-Touch Extender output found at device %d"%i)
                    if pygame.midi.get_device_info(i)[4]==0: self.midiOut = pygame.midi.Output(i)
                    else: raise ExternalDeviceNotFound('X-Touch Extender output device busy.')
        if self.midiOut==None: raise ExternalDeviceNotFound('Couldn\'t find X-Touch Extender output device.')
        if self.midiIn==None: raise ExternalDeviceNotFound('Couldn\'t find X-Touch Extender input device.')
        self.knobVal=[0,0,0,0,0,0,0,0]
        self.channel=[]
        for i in range(8):
            self.channel.append(Channel(i,self.midiIn,self.midiOut,pressAndHoldDuration,doublePressDuration,self.boundHandlers,debugMode=debugMode))
        self.lastFastTime=time.time()
        self.lastSlowTime=time.time()
        self.fastTimerCallback()
        self.slowTimerCallback()

    def bind(self,eventName,handler,channels=list(range(8))):
        if isinstance(channels,int):
            self.boundHandlers[channels][eventName]=handler
            return 0
        elif isinstance(channels,list):
            for i in channels:
                self.boundHandlers[i][eventName]=handler
            return 0
        else: return -1

    def fastTimerCallback(self):
        self.midiMessagePump()
        presentTime=time.time()
        nextTime=self.lastFastTime+FAST_TIMER_PERIOD
        self.lastFastTime=nextTime
        delayTime=nextTime-presentTime
        threading.Timer(delayTime,self.fastTimerCallback).start()

    def slowTimerCallback(self):
        self.blinkProcess()
        presentTime=time.time()
        nextTime=self.lastSlowTime+SLOW_TIMER_PERIOD
        self.lastSlowTime=nextTime
        delayTime=nextTime-presentTime
        threading.Timer(delayTime,self.slowTimerCallback).start()

    def midiMessagePump(self):
        while(self.midiIn.poll()):
            event=self.midiIn.read(1)
#            if self.debug: print(event)
            (eventType,eventControl,eventValue)=event[0][0][:3]
    #        if self.debug: print("Type=%x, Control=%d, Value=%d"%(eventType,eventControl,eventValue))
            if (eventType==0x90):                #Note
                if ((eventControl>=32)&(eventControl<=39)):
                    channel=eventControl-32
                    if (eventValue==0):
                        self.channel[channel].knob.releaseHandler()
                    elif (eventValue==127):
                        self.channel[channel].knob.pressHandler()
                    else:
                        self.unhandledEvent("Unhandled knob press event Type=0x%x Control=0x%x Value=0x%x"%(eventType,eventControl,eventValue))
                elif ((eventControl>=0)&(eventControl<=31)):
                    row=int(eventControl/8)
                    col=eventControl-(row*8)
                    if (eventValue==0):
                        self.channel[col].button[row].releaseHandler()
                    elif (eventValue==127):
                        self.channel[col].button[row].pressHandler()
                    else:
                        self.unhandledEvent("Unhandled button event Type=0x%x Control=0x%x Value=0x%x"%(eventType,eventControl,eventValue))
                elif ((eventControl>=104)&(eventControl<=111)):
                    fader=(int(eventControl)-104)
                    if eventValue==127:
                        self.faderPressHandler(fader)
                    elif eventValue==0:
                        self.faderReleaseHandler(fader)
                    else:
                        self.unhandledEvent("Unhandled fader touch value Type=0x%x Control=0x%x Value=0x%x"%(eventType,eventControl,eventValue))
                else:
                    self.unhandledEvent("Unhandled note command Type=0x%x Control=0x%x Value=0x%x"%(eventType,eventControl,eventValue))

            elif (eventType==0xB0):                #Command Change
                if ((eventControl>=16)&(eventControl<=23)):
                    channel=eventControl-16
                    if (eventValue<64):
                        self.channel[channel].knob.incrementHandler(eventValue)
                    elif (eventValue>=65):
                        self.channel[channel].knob.decrementHandler(eventValue-64)
                    else:
                        self.unhandledEvent("Unhandled knob change command Type=0x%x Control=0x%x Value=0x%x"%(eventType,eventControl,eventValue))
                else:
                    self.unhandledEvent("Unhandled command change command Type=0x%x Control=0x%x Value=0x%x"%(eventType,eventControl,eventValue))
            
            elif ((eventType>=0xe0)&(eventType<=0xe7)):
                fader=eventType-0xe0
                faderValue=eventValue*127+eventControl
                self.faderLevelHandler(fader,faderValue)

            else:
                self.unhandledEvent("Unhandled MIDI event type Type=0x%x Control=0x%x Value=0x%x"%(eventType,eventControl,eventValue))

    def blinkProcess(self):
        self.blinkStep+=1
        if self.blinkStep>15:
            self.blinkStep=0
        for entry in self.blinkTable.keys():
            blinkState=self.blinkTable[entry]&1<<self.blinkStep
            entry.blink(blinkState)
        
    def faderPressHandler(self,fader):
        if self.debug: print("Fader %d touch"%fader)
        if "FaderPress" in self.boundHandlers[fader]:
            retval={}
            retval["obj"]=self
            retval["fader"]=fader
            self.boundHandlers[fader]["FaderPress"](retval)

    def faderReleaseHandler(self,fader):
        if self.debug: print("Fader %d release"%fader)
        if "FaderRelease" in self.boundHandlers[fader]:
            retval={}
            retval["obj"]=self
            retval["fader"]=fader
            self.boundHandlers[fader]["FaderRelease"](retval)

    def faderLevelHandler(self,fader,level):
        if self.debug: print("Fader %d level %d"%(fader,level))
        if "FaderLevel" in self.boundHandlers[fader]:
            retval={}
            retval["obj"]=self
            retval["fader"]=fader
            retval["level"]=level
            self.boundHandlers[fader]["FaderLevel"](retval)

    def unhandledEvent(self,s):
        if self.debug: print(s)

    def setFader(self,fader,faderLevel):
        if (faderLevel>16256): faderLevel=16256
        if (faderLevel<0): faderLevel=0
        self.midiOut.write_short(0xE0+fader,int((int(faderLevel))%128),int((int(faderLevel))/128))

    def addBlink(self,blinkMember,blinkPattern):
        self.blinkTable[blinkMember]=blinkPattern