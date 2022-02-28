import XTouch
import eos
import time
import socket

IP=socket.gethostbyname(socket.gethostname()) #It's assumed that this script is running on the same machine as Eos.  If not, change this to the Eos machine's IP address.
IN_PORT=8000 #Eos's OSC in port
OUT_PORT=8001 #Eos's OSC out port

def xtFaderHandler(fader,level): #Custom XTouch fader event handler: sends the new level to Eos via OSC
    e.client.send_message("/eos/fader/1/{}".format(fader+1),float(level/16256))

def eosFaderHandler(page,fader,level): #Custom Eos fader event handler: sends the new fader value to the XTouch
    xt.setFader(fader-1,int(level*(16256/100)))

xt=XTouch.XTouch() #Instantiate an XTouch Extender
e=eos.eos(IP,IN_PORT,OUT_PORT) #Instantiate an Eos client and server

xt.bindHandler("FaderLevel",xtFaderHandler) #Bind our custom XTouch fader event handler
e.bindHandler("FaderLevel",eosFaderHandler) #Bind our custom Eos fader event handler
e.start() #This is blocking, so always issue it as the very last step