// Physical keys keep teleoperation independent of input method and letter case.
const KeyboardControl=(()=>{
 const physical={KeyW:'w',KeyA:'a',KeyS:'s',KeyD:'d',KeyQ:'q',KeyE:'e'};
 function key(event){if(event.code&&event.code!=='Unidentified')return physical[event.code]||null;const k=String(event.key||'').toLowerCase();return /^[wasdqe]$/.test(k)?k:null;}
 function editable(target){return !!target?.closest?.('input,textarea,select,[contenteditable]:not([contenteditable="false"])');}
 function command(keys){const has=k=>keys.has(k)?1:0;return{linear:{x:.18*(has('w')-has('s')),y:.18*(has('a')-has('d')),z:0},angular:{x:0,y:0,z:.55*(has('q')-has('e'))}};}
 return{key,editable,command};
})();
if(typeof module!=='undefined')module.exports=KeyboardControl;
