/* Timestamped planar TF buffer. Never extrapolate moving transforms. */
(function(root){
  const time=s=>Number(s?.sec||0)+Number(s?.nanosec||0)/1e9;
  const compose=(a,b)=>({x:a.x+Math.cos(a.yaw)*b.x-Math.sin(a.yaw)*b.y,y:a.y+Math.sin(a.yaw)*b.x+Math.cos(a.yaw)*b.y,yaw:a.yaw+b.yaw});
  class Buffer {
    constructor(){this.edges=new Map();}
    add(parent,child,pose){
      const key=parent+'/'+child, list=this.edges.get(key)||[];
      const i=list.findIndex(p=>p.stamp>=pose.stamp);
      if(i<0)list.push(pose);else if(list[i].stamp===pose.stamp)list[i]=pose;else list.splice(i,0,pose);
      if(list.length>400)list.splice(0,list.length-400);this.edges.set(key,list);
    }
    at(parent,child,t,hold=false,maxGap=.3){
      const list=this.edges.get(parent+'/'+child)||[];
      if(!list.length)return null;
      if(list[0].stamp===0)return list[0];
      let i=list.findIndex(p=>p.stamp>=t);
      if(i>=0&&Math.abs(list[i].stamp-t)<1e-6)return list[i];
      if(i===0)return null;
      if(hold){const p=i<0?list[list.length-1]:list[i-1];return t-p.stamp<2.5?p:null;}
      if(i<0)return null;
      const a=list[i-1],b=list[i];if(b.stamp-a.stamp>maxGap)return null;
      const f=(t-a.stamp)/(b.stamp-a.stamp),angle=Math.atan2(Math.sin(b.yaw-a.yaw),Math.cos(b.yaw-a.yaw));
      return {x:a.x+(b.x-a.x)*f,y:a.y+(b.y-a.y)*f,yaw:a.yaw+angle*f};
    }
    mapAt(t){return this.at('map','odom',t,false,2.5)||this.at('map','odom',t,true);}
    laser(scan){
      const t=time(scan.header?.stamp), frame=(scan.header?.frame_id||'').replace(/^\//,'');
      const a=this.mapAt(t),b=this.at('odom','base_link',t);
      if(!a||!b)return null;
      if(frame==='base_link')return compose(a,b);
      const c=this.at('base_link',frame,0);return c?compose(compose(a,b),c):null;
    }
  }
  const api={Buffer,time,compose};if(typeof module!=='undefined')module.exports=api;else root.ScanTransform=api;
})(typeof globalThis!=='undefined'?globalThis:this);
