/* Dependency-free orthographic 3D view of the same ROS map coordinates.
   Wall height is illustrative: OccupancyGrid contains no measured height. */
const Scene3D=(()=>{
 function viewport(width,height,map,view,camera){const res=map.resolution;return {scene:true,width,height,w:map.width,h:map.height,res,originX:map.origin.position.x,originY:map.origin.position.y,cx:map.origin.position.x+map.width*res/2,cy:map.origin.position.y+map.height*res/2,ox:width/2+view.panX,oy:height/2+view.panY,scale:Math.min(width/(map.width*res*1.45),height/(map.height*res*1.45))*view.zoom,yaw:camera.yaw,tilt:camera.tilt};}
 function project(p,v){const dx=p.x-v.cx,dy=p.y-v.cy,c=Math.cos(v.yaw),s=Math.sin(v.yaw);return{x:v.ox+(c*dx-s*dy)*v.scale,y:v.oy-(s*dx+c*dy)*Math.sin(v.tilt)*v.scale-(p.z||0)*Math.cos(v.tilt)*v.scale};}
 function unproject(p,v){const a=(p.x-v.ox)/v.scale,b=-(p.y-v.oy)/v.scale/Math.sin(v.tilt),c=Math.cos(v.yaw),s=Math.sin(v.yaw);return{x:v.cx+c*a+s*b,y:v.cy-s*a+c*b};}
 let cachedMap=null,boxes=[];
 function render(ctx,v,state,options){
  const p=a=>project(a,v),line=(points,color,width=1)=>{if(!points.length)return;ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();points.forEach((q,i)=>{const a=p(q);i?ctx.lineTo(a.x,a.y):ctx.moveTo(a.x,a.y);});ctx.stroke();};
  const polygon=(points,color)=>{ctx.fillStyle=color;ctx.beginPath();points.forEach((q,i)=>{const a=p(q);i?ctx.lineTo(a.x,a.y):ctx.moveTo(a.x,a.y);});ctx.closePath();ctx.fill();};
  const x=v.originX,y=v.originY,X=x+v.w*v.res,Y=y+v.h*v.res;
  polygon([{x,y},{x:X,y},{x:X,y:Y},{x,y:Y}],'#263b46');
  if(options.grid){for(let a=Math.ceil(x);a<=X;a++)line([{x:a,y},{x:a,y:Y}],'#405964');for(let b=Math.ceil(y);b<=Y;b++)line([{x,y:b},{x:X,y:b}],'#405964');}
  // Unknown cells remain unknown, rather than invented free space.
  if(cachedMap!==state.map){cachedMap=state.map;boxes=[];for(let row=0;row<v.h;row++){let start=-1;for(let col=0;col<=v.w;col++){const occupied=col<v.w&&state.map.data[row*v.w+col]>=50;if(occupied&&start<0)start=col;if(!occupied&&start>=0){boxes.push({x:x+start*v.res,y:y+row*v.res,w:(col-start)*v.res,h:v.res});start=-1;}}}}
  // Occupancy base texture preserves both free and unknown areas.
  if(state.mapRaster){const a=p({x,y:Y}),b=p({x:X,y:Y}),c=p({x,y});ctx.save();ctx.transform((b.x-a.x)/v.w,(b.y-a.y)/v.w,(c.x-a.x)/v.h,(c.y-a.y)/v.h,a.x,a.y);ctx.globalAlpha=.75;ctx.drawImage(state.mapRaster,0,0);ctx.restore();}
  const cost=(msg,color)=>{if(!msg)return;const info=msg.info,frame=msg.header?.frame_id||'map';if(!['map','odom'].includes(frame))return;const origin=options.pose(info.origin,frame,msg.header?.stamp);if(!origin)return;const r=info.resolution;const c=Math.cos(origin.yaw),s=Math.sin(origin.yaw);const world=(a,b)=>({x:origin.x+c*a-s*b,y:origin.y+s*a+c*b,z:.015});for(let j=0;j<info.height;j+=2)for(let i=0;i<info.width;i+=2){const n=msg.data[j*info.width+i];if(n<=0)continue;ctx.globalAlpha=.12+.35*n/100;polygon([world(i*r,j*r),world((i+2)*r,j*r),world((i+2)*r,(j+2)*r),world(i*r,(j+2)*r)],color);}ctx.globalAlpha=1;};
  if(options.globalCost)cost(state.globalCost,'#3b82f6');if(options.localCost)cost(state.localCost,'#123f91');
  const faces=[];const box=(b,z)=>{const a={x:b.x,y:b.y},d={x:b.x+b.w,y:b.y},e={x:b.x+b.w,y:b.y+b.h},f={x:b.x,y:b.y+b.h};for(const [u,w] of [[a,d],[d,e],[e,f],[f,a]])faces.push({points:[u,w,{...w,z},{...u,z}],color:'#344f60'});faces.push({points:[{...a,z},{...d,z},{...e,z},{...f,z}],color:'#668899'});};
  boxes.forEach(b=>box(b,.55));faces.sort((a,b)=>a.points.reduce((s,q)=>s+p(q).y,0)/a.points.length-b.points.reduce((s,q)=>s+p(q).y,0)/b.points.length).forEach(f=>polygon(f.points,f.color));
  const path=(msg,color)=>{if(msg)line(msg.poses.map(a=>({...options.pose(a.pose,msg.header?.frame_id||'map'),z:.07})),color,2.5);};
  if(options.global)path(state.globalPath,'#79a3ff');if(options.local)path(state.localPath,'#57ffe0');if(options.before&&state.beforeTrail)line(state.beforeTrail.map(a=>({...a,z:.06})),'#ffb0f0',2);if(options.trail)line(state.trail.map(a=>({...a,z:.04})),'#cd8cff',1.5);
  if(options.scan&&state.scanPose&&Date.now()-state.scanResolvedAt<1000){const a=state.scanPose;ctx.fillStyle='#5ffff0';(state.scan.ranges||[]).forEach((r,i)=>{if(!Number.isFinite(r)||r<=state.scan.range_min||r>=state.scan.range_max)return;const t=a.yaw+state.scan.angle_min+i*state.scan.angle_increment,q=p({x:a.x+r*Math.cos(t),y:a.y+r*Math.sin(t),z:.12});ctx.fillRect(q.x-1.4,q.y-1.4,2.8,2.8);});}
  const cylinder=(o,r,z,color)=>{const bottom=[],top=[];for(let i=0;i<=32;i++){const t=i/32*Math.PI*2,q={x:o.x+r*Math.cos(t),y:o.y+r*Math.sin(t)};bottom.push(q);top.push({...q,z});}polygon([...bottom,...top.slice().reverse()],color);polygon(top,color);line(top,'#c2d8d9',1);};
  Object.values(state.obstacles||{}).forEach(o=>cylinder(o,o.radius,.45,'#c88c49'));
  if(state.gesture?.kind==='move'&&state.gesture.preview)cylinder(state.gesture.preview,state.gesture.obstacle.radius,.47,'#ffd28a');
  const arrow=(o,color)=>{const z=.22,a={...o,z},b={x:o.x+.65*Math.cos(o.yaw||0),y:o.y+.65*Math.sin(o.yaw||0),z};line([a,b],color,3);for(const t of [-.5,.5])line([b,{x:b.x-.23*Math.cos((o.yaw||0)+t),y:b.y-.23*Math.sin((o.yaw||0)+t),z}],color,3);};
  if(state.robot){cylinder(state.robot,state.robotRadius||.3,.18,'#93df6b');arrow(state.robot,'#d9ffb6');}
  if(state.target)arrow(state.target,'#ffdc80');if(state.gesture?.kind==='pose')arrow({...state.gesture.start,yaw:state.gesture.yaw},'#ff91c8');
  ctx.font='12px sans-serif';ctx.fillStyle='#c7dce6';ctx.fillText('3D 示意 · 墙高非实测 · 激光为真实二维扫描（未伪造三维点云）',16,v.height-62);
 }
 return {viewport,project,unproject,render};
})();
if(typeof module!=='undefined')module.exports=Scene3D;
