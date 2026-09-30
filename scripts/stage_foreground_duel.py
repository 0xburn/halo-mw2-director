#!/usr/bin/env python3
"""Two-player exchange for the native battlefield: attack, evade, counter, re-peek."""
def stage(scene):
    by={a['id']:a for a in scene['actors']};mw=by[6];chief=by[11]
    ATTACK,SPRINT,JUMP,ADS,CROUCH=1,2,1024,2048,512
    def target(start,end,who,**kw):return dict(start=start,end=end,actor=who,height=42,turn_speed=460,response=26,**kw)
    def point(start,end,xyz):return dict(start=start,end=end,point=xyz,turn_speed=420,response=24)
    # In the open lane south of the pickup. Both opponents keep their distance;
    # each committed shot is followed by a purposeful change of position.
    mw['route']=[[0,-130,220,-210],[10.5,-130,220,-232],[11.22,-70,320,-232],
      [11.9,-70,320,-232],[12.5,-205,285,-232],[12.9,-205,285,-232],
      [13.5,-130,220,-236],[24,-130,220,-236]]
    chief['route']=[[0,20,530,-236],[11.10,20,530,-236],[11.63,110,515,-236],
      [12.15,110,515,-236],[12.9,-10,430,-236],[14.23,-10,430,-236],
      [15.65,-166,248,-232],[24,-166,248,-232]]
    mw['aim']=[target(0,10.5,11),target(11.08,11.38,11),point(11.38,11.65,[30,530,-195]),
      target(12.5,13.52,11,offset_z=22)]
    chief['aim']=[target(0,11.85,6),point(11.85,12.2,[-70,320,-195]),
      target(12.9,14.22,6),point(14.22,24,[-130,220,-234])]
    mw['buttons']=[[10.5,11.15,SPRINT],[11.25,11.86,ADS],[11.60,11.84,ATTACK],
      [11.95,12.48,SPRINT],[12.5,12.76,CROUCH],[12.91,13.0,SPRINT],
      [13.02,13.13,JUMP],[13.15,13.62,ADS],[13.44,13.60,ATTACK]]
    chief['buttons']=[[11.85,12.2,ADS],[12.01,12.12,ATTACK],[12.22,12.83,SPRINT],
      [13.13,13.65,CROUCH],[13.65,14.15,ADS],[13.92,14.12,ATTACK]]
    # Keep the two missed rounds readable without ambient damage ending the duel.
    mw['damage_from']=[11];chief['damage_from']=[]
    for k in range(13):
      t=15.9+k*.64
      if t<24:chief['buttons'].append([t,t+.34,CROUCH])
    scene['title']='Rust: Warthog chaos, with a staged foreground sniper duel'
    return scene
