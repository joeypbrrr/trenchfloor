/* Cosmetic only. Atomic synchronous reservations keep desks and rooms safe. */
(function(root){
class FloorOccupancy {
  constructor(){this.cap={bathroom:1,treadmill0:1,treadmill1:1,kitchen:2};this.agents=Array.from({length:6},()=>({state:'home',spot:null}));}
  deskCount(){return this.agents.filter(a=>a.state==='home').length;}
  used(spot){return this.agents.filter(a=>a.spot===spot).length;}
  depart(i,spot){const a=this.agents[i];if(!a||a.state!=='home'||this.deskCount()<=3||!this.cap[spot]||this.used(spot)>=this.cap[spot])return false;const used=new Set(this.agents.filter(x=>x.spot===spot).map(x=>x.slot));a.slot=Array.from({length:this.cap[spot]},(_,n)=>n).find(n=>!used.has(n));a.state='outbound';a.spot=spot;return true;}
  arrive(i){if(this.agents[i].state==='outbound')this.agents[i].state='visiting';}
  returnHome(i){if(this.agents[i].state!=='home')this.agents[i].state='returning';}
  home(i){this.agents[i]={state:'home',spot:null};}
}
root.FloorOccupancy=FloorOccupancy;if(typeof module!=='undefined')module.exports=FloorOccupancy;
})(typeof window!=='undefined'?window:globalThis);
