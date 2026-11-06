const test=require('node:test'),assert=require('node:assert/strict');
const tools=require('../src/rm_nav_training_lab/web/parameter_tools.js');
const cost=['/global_costmap/global_costmap','inflation_layer.inflation_radius',.55];
const speed=['/controller_server','FollowPath.max_vel_x',.5];
const critic=['/controller_server','FollowPath.PathDist.scale',32];
test('separate global blue and local dark blue',()=>{assert.equal(tools.palette.global,'#3b82f6');assert.equal(tools.palette.local,'#123f91');});
test('commands use input value and preserve double type',()=>{const s=tools.commands(cost,'1');assert.match(s,/inflation_layer.inflation_radius 1\.0/);assert.ok(!s.includes('VALUE'));assert.match(s,/mkdir -p/);});
test('dynamic speed does not interrupt navigation',()=>{assert.equal(tools.metadata(speed).reload,false);assert.ok(!tools.commands(speed,'.2').includes('cancel_goal'));});
test('critic reload commands pause, cleanup, apply, configure, resume in order',()=>{const s=tools.commands(critic,'40');assert.ok(s.indexOf('cancel_goal')<s.indexOf("command: 1"));assert.ok(s.indexOf('cleanup')<s.indexOf('FollowPath.PathDist.scale 40.0'));assert.ok(s.indexOf('configure')<s.indexOf('command: 2'));});
test('invalid, empty and out-of-envelope input is rejected',()=>{for(const input of ['','NaN',Infinity,-1,4])assert.throws(()=>tools.validate(cost,input));});

test('CLI targets the actual connected ROS domain',()=>{assert.match(tools.commands(cost,'.7',61),/export ROS_DOMAIN_ID=61/);assert.throws(()=>tools.commands(cost,'.7',-1));});

test('raster keeps unknown/free transparent, blue costs and bottom-left ROS ordering',()=>{const rgba=tools.costmapPixels(2,2,[100,50,0,-1],tools.palette.global,.5);assert.deepEqual(Array.from(rgba.slice(0,8)),[0,0,0,0,0,0,0,0]);assert.deepEqual(Array.from(rgba.slice(8,12)),[59,130,246,128]);assert.equal(rgba[15],64);});
test('grouped speed supports 2 m/s and refreshes Humble combined-speed cache after all limits',()=>{const p=['/controller_server','training_speed',.8];assert.equal(tools.validate(p,1.5),1.5);assert.throws(()=>tools.validate(p,2.1));const s=tools.commands(p,1.5);for(const key of ['max_vel_x','max_vel_y','min_vel_x','min_vel_y','max_speed_xy'])assert.ok(s.includes('FollowPath.'+key));assert.ok(s.indexOf('FollowPath.max_speed_xy 1.5')<s.indexOf('ros2 param set /controller_server FollowPath.min_speed_theta'));assert.match(s,/FollowPath.min_vel_y -1\.5/);assert.ok(!s.includes('ros2 param set /controller_server training_speed'));assert.ok(!s.includes('cancel_goal'));});
test('obstacle critic exposes meaningful small increments and reload semantics',()=>{const m=tools.metadata(['/controller_server','FollowPath.BaseObstacle.scale',.02]);assert.equal(m.reload,true);assert.ok(m.step<.02);});
