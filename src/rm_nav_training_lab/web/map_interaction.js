// Geometry for an RViz-style 2D viewport. No browser or ROS dependencies.
const MapInteraction=(()=>{
 function viewport(width,height,map,view){
  const w=map.width,h=map.height,scale=Math.min(width/w,height/h)*view.zoom;
  return {w,h,scale,ox:(width-w*scale)/2+view.panX,oy:(height-h*scale)/2+view.panY,originX:map.origin.position.x,originY:map.origin.position.y,res:map.resolution};
 }
 function toScreen(point,v){return {x:v.ox+(point.x-v.originX)/v.res*v.scale,y:v.oy+v.h*v.scale-(point.y-v.originY)/v.res*v.scale};}
 function toWorld(point,v){return {x:v.originX+(point.x-v.ox)/v.scale*v.res,y:v.originY+(v.h-(point.y-v.oy)/v.scale)*v.res};}
 function zoomAt(view,point,factor,width,height,map){
  const old=viewport(width,height,map,view),world=toWorld(point,old),zoom=Math.max(.6,Math.min(12,view.zoom*factor));
  const next={...view,zoom},screen=toScreen(world,viewport(width,height,map,next));next.panX+=point.x-screen.x;next.panY+=point.y-screen.y;return next;
 }
 function heading(start,end,fallback=0){return Math.hypot(end.x-start.x,end.y-start.y)<.02?fallback:Math.atan2(end.y-start.y,end.x-start.x);}
 return {viewport,toScreen,toWorld,zoomAt,heading};
})();
if(typeof module!=='undefined')module.exports=MapInteraction;
