#!/usr/bin/env python3
"""Layer locally extracted Halo CE collision audio; no game audio is shipped."""
import math, struct, wave
from pathlib import Path

def mix_impact(pack):
    rate=22050; out=[0.] * int(rate*1.1)
    # Blood transient, chassis crash, and a lower collision layer for body.
    for name,gain,speed in [('halo-splat',1.8,1.),('halo-vehicle-impact',2.6,1.),('halo-vehicle-impact',1.7,.64),('warthog-impact',.6,.85)]:
        with wave.open(str(pack/(name+'.wav')),'rb') as source:
            assert source.getsampwidth()==2
            channels=source.getnchannels();sr=source.getframerate()
            raw=source.readframes(source.getnframes())
        values=struct.unpack('<'+'h'*(len(raw)//2),raw)
        mono=[sum(values[j:j+channels])/(channels*32768.) for j in range(0,len(values),channels)]
        for i in range(min(len(out),int(len(mono)*rate/(sr*speed)))):
            at=i*sr*speed/rate;j=int(at);f=at-j
            out[i]+=gain*(mono[j]*(1-f)+mono[min(j+1,len(mono)-1)]*f)
    # A short falling bass hit makes the collision read under the engine.
    for i in range(int(rate*.16)):
        t=i/rate;out[i]+=.58*math.sin(2*math.pi*(95*t-145*t*t))*math.exp(-t*24)*min(1,t/.003)
    samples=[int(30000*math.tanh(v*1.5)) for v in out]
    with wave.open(str(pack/'warthog-splat.wav'),'wb') as dst:
        dst.setnchannels(1);dst.setsampwidth(2);dst.setframerate(rate)
        dst.writeframes(struct.pack('<'+'h'*len(samples),*samples))
    print('Layered Halo vehicle impact:',pack/'warthog-splat.wav')

if __name__=='__main__':mix_impact(Path(__file__).resolve().parents[1]/'local-assets/halo/native')
