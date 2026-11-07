"""Display-only regression coverage; never reads or mutates a paper account."""
import json,re,shutil,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PositionDisplayTests(unittest.TestCase):
 def test_position_first_on_both_routes(self):
  for path in ('index.html','live/index.html'):
   s=(ROOT/path).read_text()
   self.assertLess(s.index('id="openPositionPanel"'),s.index('<section class="floor-card"'))
   self.assertLess(s.index('<section class="floor-card"'),s.index('<section class="intro"'))
   self.assertEqual(s.count('id="openPositions"'),1)
   if path=='index.html':
    self.assertIn('#liveChat{max-height:360px!important',s)
    self.assertIn('#liveChat{max-height:280px!important',s)
    self.assertIn("e.kind==='trade_review'",s)
   else:
    self.assertIn('#liveChat{max-height:none!important',s)
   self.assertIn('NEWEST FIRST',s)
  self.assertIn('src="./occupancy.js"',(ROOT/'live/index.html').read_text())

 @unittest.skipUnless(shutil.which('node'),'Node required for DOM-unit checks')
 def test_rendered_position_details_badge_counts_and_empty_state(self):
  s=(ROOT/'index.html').read_text();code=s[s.index('function precisePrice'):s.index('function tokenCard')]
  fmt=s[s.index('const ET_FMT ='):s.index('const todayET =')]
  js=DOM+fmt+"\nlet state=null; const $=id=>nodes[id]; const empty=text=>{const e=new E();e.textContent=text;return e;};\n"+code+"""
 const p={id:'p',symbol:'COGE',name:'COGE COIN',tier:'primary',entry_time:'2026-11-07T05:00:09Z',entry_price:.01566,notional_usd:100,stop_fraction:.12,target_fraction:.35,max_hold_seconds:57600,pool:'pool'};
 Date.now=()=>Date.parse('2026-11-07T05:30:09Z');
 state={paper_account:{positions:[p]},ledger:{trade_count:0},next_cycle:'2026-11-07T06:00:09Z'};
 renderOpenPositions(state);let text=nodes.openPositions.textContent;
 for(const x of ['COGE','NEW','$100.00','$0.01566','PRIMARY','Opened Nov 7, 2026, 12:00:09 AM ET','$0.0137808','$0.021141','Nov 7, 2026, 4:00:09 PM ET','DexScreener'])assert(text.includes(x),x+' absent: '+text);
 assert(nodes.heroTeamTrades.textContent.includes('1 open / 0 closed'));
 Date.now=()=>Date.parse('2026-11-07T06:00:09Z');assert(!positionCard(p).textContent.includes('NEW'));
 const entryStrong=nodes.openPositions.children[0].children[1].children[1].children[1];
 assert(entryStrong.title==='price $0.01566', entryStrong.title);
 state.watchlist=[{mint:'COGE',price_usd:.01566,market_cap_usd:15599028}];
 state.paper_account.positions=[{...p,mint:'COGE'}];
 renderOpenPositions(state); text=nodes.openPositions.textContent;
 for(const x of ['ENTRY MCAP','$15.60M','STOP · 12% MCAP','$13.73M','TARGET · 35% MCAP','$21.06M'])assert(text.includes(x),x+' absent: '+text);
 assert(!text.includes('$0.01566'), text);
 assert(nodes.openPositions.children[0].children[1].children[1].children[1].title==='price $0.01566');
 const closed={mint:'COGE',entry_price:.01566,exit_price:.01566*0.88,stop_fraction:.12,target_fraction:.35};
 assert(formatMc(tradeLevels(closed).exitMc)==='$13.73M');
 assert(levelQuote(tradeLevels(closed).exitMc, closed.exit_price).title.startsWith('price $'));
 state.watchlist=[];
 assert(snapshotSupply({mint:'X',entry_price:1,market_cap_usd:1000000})===null);
 assert(formatMc(tradeLevels({entry_price:2,entry_market_cap_usd:2000000,stop_fraction:.12,target_fraction:.35}).entryMc)==='$2.00M');
 assert(formatMc(tradeLevels({mint:'Z',entry_price:.5,price_usd:1,market_cap_usd:1000000,stop_fraction:.12,target_fraction:.35}).entryMc)==='$500K');
 state.watchlist=[{mint:'Z',price_usd:10,market_cap_usd:1000},{mint:'Z',price_usd:.5,market_cap_usd:500000}];
 assert(formatMc(tradeLevels({mint:'Z',entry_price:.5,stop_fraction:.12,target_fraction:.35}).entryMc)==='$500K');
 state={paper_account:{positions:[]},ledger:{trade_count:2},next_cycle:'2026-11-07T06:00:09Z'};renderOpenPositions(state);
 assert(nodes.openPositions.textContent==='No open position · next cycle 01:00 ET');assert(nodes.heroTeamTrades.textContent.includes('0 open / 2 closed'));
 """
  subprocess.run(['node','-e',js],check=True,capture_output=True,text=True)

 @unittest.skipUnless(shutil.which('node'),'Node required for DOM-unit checks')
 def test_newest_first_with_expanded_recent_and_collapsed_history(self):
  s=(ROOT/'index.html').read_text();a=s.index("  const chat=document.getElementById('liveChat');");b=s.index("  const checklist=document.getElementById('liveChecklist');",a)
  js=DOM+"\nconst AGENTS=[];const et=x=>x;const empty=x=>new E();function render(s){\n"+s[a:b]+"\n}\n"+"""
 const chat=Array.from({length:30},(_,i)=>({time:new Date(Date.UTC(2026,10,7,5,i)).toISOString(),agent:'Agent',text:'message '+i,kind:'trade_review'}));
 chat.push({time:new Date(Date.UTC(2026,10,7,8,0)).toISOString(),agent:'System',kind:'info',text:'CYCLE SCAN'});
 chat.push({time:new Date(Date.UTC(2026,10,7,8,1)).toISOString(),agent:'Strategist',kind:'loss_review',text:'RULE-BASED LOSS REVIEW / extra'});
 render({chat});
 assert(nodes.liveChat.children.length===25);assert(nodes.liveChat.children[0].textContent.includes('message 29'));assert(!nodes.liveChat.textContent.includes('CYCLE SCAN'));assert(!nodes.liveChat.textContent.includes('RULE-BASED'));assert(nodes.liveChat.children[23].textContent.includes('message 6'));
 const older=nodes.liveChat.children[24];assert(older.tag==='details');assert(older.children.length===7);assert(older.children[1].textContent.includes('message 5'));
 """
  subprocess.run(['node','-e',js],check=True,capture_output=True,text=True)

DOM="""
const assert=require('node:assert/strict');
class E{constructor(tag='div'){this.tag=tag;this.children=[];this.dataset={};this.style={};this._text='';}append(...a){this.children.push(...a);}replaceChildren(...a){this._text='';this.children=a;}set textContent(x){this._text=x;this.children=[];}get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}}
const nodes={openPositions:new E(),heroTeamTrades:new E(),liveChat:new E()};
const document={createElement:x=>new E(x),getElementById:x=>nodes[x]};
"""
