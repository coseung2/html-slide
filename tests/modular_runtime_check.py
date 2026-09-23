"""Focused runtime and deliberately-broken QA regression checks."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import build_deck
from tools.verify_modular import GEOMETRY, launch_options
from playwright.sync_api import sync_playwright

class RuntimeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(**launch_options())
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop()
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1920,'height':1080},reduced_motion='no-preference')
        self.page=self.context.new_page()
    def tearDown(self):self.context.close()
    def deck(self,value=12345.25,motion='number-count'):
        spec={'schemaVersion':1,'title':'Runtime fixture','language':'en','theme':'tech','slides':[{'id':'sample','title':'Fixture','communication_goal':'Verify a complete metric','intent':'kpi','layout':'split-left','blocks':[{'id':'metric','module':'metric','data':{'label':'Synthetic value','value':value}}],'motion':[{'module':motion,'target':'metric','reason':'Verify numeric emphasis'}]}]}
        raw,_=build_deck(spec);self.page.set_content(raw,wait_until='load');self.page.evaluate('document.fonts.ready')
    def value(self):return self.page.locator('[data-number]').text_content()
    def test_number_roll_reversal_and_static(self):
        self.deck();self.assertEqual(self.value(),'0');self.page.evaluate('__deckNext()');self.page.wait_for_timeout(580)
        self.assertEqual(self.value(),'12,345.25');self.page.evaluate('__deckPrev()');self.assertEqual(self.value(),'0')
        self.page.evaluate('__deckShell.setStatic(true)');self.assertEqual(self.value(),'12,345.25')
    def test_negative_number_settles(self):
        self.deck(-12.75);self.page.evaluate('__deckNext()');self.page.wait_for_timeout(580);self.assertEqual(self.value(),'-12.75')
    def test_cancellation_does_not_overwrite_static(self):
        self.deck();self.page.evaluate('__deckNext();__deckShell.setStatic(true)');self.page.wait_for_timeout(580);self.assertEqual(self.value(),'12,345.25')
    def test_focus_does_not_change_numeric_information(self):
        self.deck(motion='focus');self.assertEqual(self.value(),'12,345.25');self.page.evaluate('__deckNext()');self.assertEqual(self.value(),'12,345.25')
    def test_slide_entry_starts_stable_not_final_to_start(self):
        spec={'schemaVersion':1,'title':'Entry fixture','language':'en','theme':'tech','slides':[
            {'id':'first','title':'First','communication_goal':'Provide a starting slide','intent':'kpi','layout':'split-left',
             'blocks':[{'id':'m1','module':'metric','data':{'label':'First','value':1}}]},
            {'id':'second','title':'Second','communication_goal':'Verify entry phase stability','intent':'kpi','layout':'split-left',
             'blocks':[{'id':'m2','module':'metric','data':{'label':'Second','value':2}}],
             'motion':[{'module':'number-count','target':'m2','reason':'Declare a real second phase'}]}
        ]}
        raw,_=build_deck(spec);self.page.set_content(raw,wait_until='load');self.page.evaluate('document.fonts.ready')
        self.page.add_style_tag(content=".deck-live [data-slide='second'] [data-number]{transition:opacity .35s linear}.deck-live [data-slide='second'].deck-step-0 [data-number]{opacity:0}")
        self.page.evaluate('__deckGoto(0,0);__deckNext()')
        target=self.page.locator("[data-slide='second'] [data-number]")
        self.assertLess(float(target.evaluate("el=>getComputedStyle(el).opacity")),.02)
        self.page.wait_for_timeout(80)
        self.assertLess(float(target.evaluate("el=>getComputedStyle(el).opacity")),.02)
    def test_qa_detects_deliberately_overflowing_copy(self):
        self.deck(motion='focus');self.page.evaluate('__deckShell.setStatic(true)');self.assertEqual(self.page.evaluate(GEOMETRY)['errors'],[])
        self.page.add_style_tag(content='.copy{width:2500px!important}')
        self.assertIn('safe-area',{e['kind']for e in self.page.evaluate(GEOMETRY)['errors']})
    def test_qa_detects_unbound_highlight(self):
        self.deck(motion='focus');self.page.evaluate("document.querySelector('[data-hl]').dataset.target='#missing'")
        self.assertIn('unbound-highlight',{e['kind']for e in self.page.evaluate(GEOMETRY)['errors']})

if __name__=='__main__':unittest.main()
