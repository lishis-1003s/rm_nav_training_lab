// Pure parameter metadata/command helpers; no ROS changes occur in this module.
const ParameterTools = (() => {
  const palette={global:'#3b82f6',local:'#123f91'};
  function metadata(p){
    const name=p[1];
    if(name==='training_speed')return {min:.1,max:2,step:.1,reload:false,effect:'联动 DWB 前后、横移及合速度上限（0.1～2.0 m/s）；平滑器预设允许 2.0 m/s，不再卡在 0.5。',observe:'长直道分别运行 0.3 与 1.5 m/s，对比 /odom 实测合速度、峰值与到达时间。上限不是恒定速度，转弯和避障会减速。'};
    if(name==='inflation_layer.inflation_radius')return {min:0,max:3,step:.05,reload:false,effect:'障碍周围的代价缓冲范围；增大后通常离障碍更远。不会改变真实底盘尺寸。',observe:'开启对应 Costmap 图层，比较膨胀范围；路径是否改变取决于当前可达空间。'};
    if(name==='inflation_layer.cost_scaling_factor')return {min:.1,max:30,step:.1,reload:false,effect:'代价随离障碍距离增加而衰减的速度；数值越大，衰减越快。',observe:'固定膨胀半径，比较蓝色梯度分布和规划路径。'};
    if(name==='FollowPath.BaseObstacle.scale')return {min:0,max:1,step:.005,reload:true,effect:'DWB 对轨迹穿越局部代价区域的惩罚权重，数值越大通常越排斥高代价轨迹。',observe:'固定局部膨胀参数，对比 .02 和 .15 的局部轨迹与实际行驶轨迹，过大会导致停滞。'};
    if(name.endsWith('.scale'))return {min:0,max:100,step:1,reload:true,effect:name.includes('PathDist')?'局部控制评分中贴近全局路径的权重，不是避障安全距离。':'局部控制评分中接近目标的权重，不是目标容差。',observe:'会取消导航并重新配置控制器；重发同一目标，比较局部轨迹与实际运动。'};
    if(name.includes('tolerance'))return {min:.01,max:1,step:.01,reload:false,effect:name.includes('xy_goal')?'到达目标的平面距离容差；更小的值要求更精确停车。':'规划目标附近寻找可达终点的容差，不等于控制器停车精度。',observe:'新任务使用相同目标，比较规划终点、到达位置和 Action 结果。'};
    if(name.includes('acc_lim'))return {min:.05,max:5,step:.05,reload:false,effect:'DWB 采样可达到的加速度；实际输出仍受 velocity_smoother 的加减速约束。',observe:'比较 /cmd_vel、/training/sim_cmd_vel 和 /odom，二维模型不模拟电机动力学。'};
    return {min:.05,max:name.includes('theta')?2.5:2,step:.05,reload:false,effect:'DWB 的速度上限；实际速度还受合速度上限、最小速度和 velocity_smoother 限制。建议优先用联动速度上限，同时改变各方向和合速度约束。',observe:'导航中可动态调整；同时观察速度曲线和实际运动，不能只看参数回读。'};
  }
  function validate(p,raw){
    if(String(raw).trim()==='')throw Error('请先填写参数值');
    const value=Number(raw),m=metadata(p);
    if(!Number.isFinite(value)||value<m.min||value>m.max)throw Error(`本教学面板范围为 ${m.min}～${m.max}，更大范围需同时核对完整 YAML 与限速链路`);
    return value;
  }
  function doubleLiteral(value){return Number.isInteger(value)?value.toFixed(1):String(value);}
  function commands(p,raw,domain=0){
    if(!Number.isInteger(domain)||domain<0)throw Error('ROS 域 ID 无效');
    const m=metadata(p),v=doubleLiteral(validate(p,raw)),target=`${p[0]} ${p[1]}`;
    const lines=['# 在已 source ROS 与工作区环境的终端逐条执行',`export ROS_DOMAIN_ID=${domain}`,`ros2 param get ${p[0]} ${p[1]==='training_speed'?'FollowPath.max_speed_xy':p[1]}`];
    if(m.reload)lines.push(
      '# 此评分权重需要重载：先取消全部导航目标，再确认反馈已结束',
      "ros2 service call /navigate_to_pose/_action/cancel_goal action_msgs/srv/CancelGoal '{}'",
      '# 确认目标已取消后，逐条执行；每条服务均需返回 success: true',
      "ros2 service call /lifecycle_manager_navigation/manage_nodes nav2_msgs/srv/ManageLifecycleNodes '{command: 1}'",
      "ros2 lifecycle set /controller_server cleanup");
    if(p[1]==='training_speed'||p[1]==='FollowPath.max_speed_xy')lines.push('# Humble DWB：保存角速度阈值，写合速度后用原值刷新缓存', 'training_theta_min=$(ros2 param get /controller_server FollowPath.min_speed_theta --hide-type)');
    if(p[1]==='training_speed'){for(const name of ['max_vel_x','max_vel_y','min_vel_x','min_vel_y','max_speed_xy'])lines.push(`ros2 param set /controller_server FollowPath.${name} ${name.startsWith('min')?'-':''}${v}`);}
    else lines.push(`ros2 param set ${target} ${v}`);
    if(p[1]==='training_speed'||p[1]==='FollowPath.max_speed_xy')lines.push('ros2 param set /controller_server FollowPath.min_speed_theta "$training_theta_min"');
    if(m.reload)lines.push('ros2 lifecycle set /controller_server configure',"ros2 service call /lifecycle_manager_navigation/manage_nodes nav2_msgs/srv/ManageLifecycleNodes '{command: 2}'",'# 恢复后重新发送相同目标，比较轨迹与速度');
    lines.push(`ros2 param get ${p[0]} ${p[1]==='training_speed'?'FollowPath.max_speed_xy':p[1]}`,'# 运行时修改不会自动写回 Launch 使用的 YAML','mkdir -p ~/rm_training_evidence',`ros2 param dump ${p[0]} > ~/rm_training_evidence/parameter_snapshot.yaml`);
    return lines.join('\n');
  }
  function costmapPixels(width,height,data,color,maxAlpha){
    const rgba=new Uint8ClampedArray(width*height*4),rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16));
    for(let i=0;i<Math.min(width*height,data.length);i++){
      const value=Number(data[i]);if(value<=0)continue;
      const row=Math.floor(i/width),col=i%width,offset=((height-1-row)*width+col)*4;
      rgba.set(rgb,offset);rgba[offset+3]=Math.round(255*maxAlpha*Math.max(.08,Math.min(1,value/100)));
    }
    return rgba;
  }
  return {palette,metadata,validate,commands,costmapPixels};
})();
if(typeof module!=='undefined')module.exports=ParameterTools;
