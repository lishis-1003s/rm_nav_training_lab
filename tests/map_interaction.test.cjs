const test=require('node:test'),assert=require('node:assert/strict');
const M=require('../src/rm_nav_training_lab/web/map_interaction.js');
const map={width:252,height:172,resolution:.05,origin:{position:{x:-6.3,y:-4.3}}},view={zoom:1,panX:0,panY:0};
function near(a,b){assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);}
test('world and screen transforms round trip with zoom and pan',()=>{const v=M.viewport(900,600,map,{zoom:3,panX:70,panY:-20}),p={x:2.3,y:-1.2},q=M.toWorld(M.toScreen(p,v),v);near(q.x,p.x);near(q.y,p.y);});
test('zoom keeps the point under the cursor fixed',()=>{const p={x:300,y:150},a=M.toWorld(p,M.viewport(900,600,map,view)),next=M.zoomAt(view,p,2,900,600,map),b=M.toWorld(p,M.viewport(900,600,map,next));near(a.x,b.x);near(a.y,b.y);});
test('zoom clamps its bounds without moving the anchor',()=>{const p={x:40,y:50},next=M.zoomAt(view,p,100,900,600,map);assert.equal(next.zoom,12);const a=M.toWorld(p,M.viewport(900,600,map,view)),b=M.toWorld(p,M.viewport(900,600,map,next));near(a.x,b.x);near(a.y,b.y);});
test('drag heading follows ROS map coordinates and short clicks preserve heading',()=>{near(M.heading({x:0,y:0},{x:0,y:1}),Math.PI/2);near(M.heading({x:0,y:0},{x:.001,y:0},1),1);});
