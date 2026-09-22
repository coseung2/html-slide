"""Deterministic contracts for AI-authored module compositions."""
from __future__ import annotations
import base64
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Registry, plan_deck, build_deck
from core.composer import assign_slots
from core.registry import ContractError, identifier
from core.renderers import media_data, fmt
from core.validation import load_spec, safe_url

ROOT=Path(__file__).resolve().parents[1]
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.registry=Registry(ROOT)
        self.spec={'schemaVersion':1,'title':'Test deck','language':'en','theme':'tech','slides':[{
          'id':'one','title':'One','communication_goal':'Explain one point','intent':'thesis',
          'blocks':[{'id':'message','module':'statement','data':{'text':'One complete idea.'}}]}]}
    def reject(self,spec):
        with self.assertRaises(ContractError):plan_deck(spec,self.registry)
    def test_counts(self):
        self.assertEqual({f:len(self.registry.list(f))for f in ['layouts','content','visuals','motion','themes','typography','palettes','dataviz']},
          {'layouts':12,'content':11,'visuals':4,'motion':7,'themes':7,'typography':7,'palettes':8,'dataviz':5})
    def test_search_intent(self):
        self.assertEqual(self.registry.search(intent='ranking',theme='sports-broadcast')[0]['id'],'ranking-board')
    def test_search_deterministic(self):self.assertEqual(self.registry.search(intent='comparison'),self.registry.search(intent='comparison'))
    def test_style_search_deterministic(self):
        args={'theme':'education','language':'ko','domain':'education','audience':'elementary','tone':['approachable','clear'],'density':'medium'}
        self.assertEqual(self.registry.style_search('typography',**args),self.registry.style_search('typography',**args))
    def test_auto_art_direction_by_theme(self):
        plan=plan_deck(self.spec,self.registry)
        self.assertEqual(plan['styles']['typography']['id'],'tech-modern')
        self.assertEqual(plan['styles']['palette']['id'],'midnight-blue')
        self.assertEqual(plan['styles']['dataviz']['id'],'categorical-6')
        self.assertEqual(plan['styles']['typography']['mode'],'auto')
        self.assertTrue(plan['styles']['typography']['reasons'])
    def test_education_signals_choose_classroom_sets(self):
        self.spec['theme']='education';self.spec['style']={'signals':{'domain':'education','audience':'elementary','tone':['approachable','clear'],'density':'medium'}}
        plan=plan_deck(self.spec,self.registry)
        self.assertEqual(plan['styles']['typography']['id'],'classroom-friendly')
        self.assertEqual(plan['styles']['palette']['id'],'classroom-warm')
        self.assertEqual(plan['styles']['dataviz']['id'],'categorical-soft')
    def test_signals_can_override_theme_default(self):
        self.spec['theme']='education';self.spec['style']={'signals':{'domain':'business','audience':'professional','tone':['modern'],'density':'high'}}
        self.assertEqual(plan_deck(self.spec,self.registry)['styles']['typography']['id'],'clean-sans')
    def test_explicit_art_direction_override(self):
        self.spec['style']={'typography':'clean-sans','palette':'monochrome','dataviz':'sequential-blue'}
        html,plan=build_deck(self.spec,self.registry)
        self.assertEqual(plan['styles']['typography']['mode'],'explicit')
        self.assertIn('data-typography="clean-sans"',html)
        self.assertIn('data-palette="monochrome"',html)
        self.assertIn('data-dataviz="sequential-blue"',html)
        self.assertIn('body[data-palette="monochrome"]{--paper:',html)
        self.assertNotIn('body[data-palette="midnight-blue"]{--paper:',html)
    def test_unknown_art_direction_rejected(self):
        self.spec['style']={'palette':'missing'};self.reject(self.spec)
    def test_unknown_style_property_rejected(self):
        self.spec['style']={'shadow':'dramatic'};self.reject(self.spec)
    def test_unknown_search_theme(self):
        with self.assertRaises(ContractError):self.registry.search(theme='missing')
    def test_catalog_serializable(self):json.dumps(self.registry.catalog())
    def test_catalog_separates_style_packs(self):
        catalog=self.registry.catalog();self.assertEqual(len(catalog['styles']),20)
        self.assertTrue(all(x['type'] in ('typography','palettes','dataviz') for x in catalog['styles']))
    def test_no_shared_mutation(self):
        x=self.registry.get('layouts','hero');x['slots'].clear();self.assertTrue(self.registry.get('layouts','hero')['slots'])
    def test_default_auto_layout(self):self.assertEqual(plan_deck(self.spec,self.registry)['slides'][0]['layout'],'hero')
    def test_explicit_layout(self):
        self.spec['slides'][0]['layout']='split-right';self.assertEqual(plan_deck(self.spec,self.registry)['slides'][0]['layout'],'split-right')
    def test_no_input_mutation(self):
        before=copy.deepcopy(self.spec);build_deck(self.spec,self.registry);self.assertEqual(self.spec,before)
    def test_deterministic_build(self):self.assertEqual(build_deck(self.spec,self.registry),build_deck(self.spec,self.registry))
    def test_unknown_module(self):self.spec['slides'][0]['blocks'][0]['module']='missing';self.reject(self.spec)
    def test_unknown_theme(self):self.spec['theme']='missing';self.reject(self.spec)
    def test_unknown_layout(self):self.spec['slides'][0]['layout']='missing';self.reject(self.spec)
    def test_wrong_schema_version(self):self.spec['schemaVersion']=2;self.reject(self.spec)
    def test_unknown_property(self):self.spec['tite']='typo';self.reject(self.spec)
    def test_unknown_block_property(self):self.spec['slides'][0]['blocks'][0]['style']='position:fixed';self.reject(self.spec)
    def test_empty_deck(self):self.spec['slides']=[];self.reject(self.spec)
    def test_goal_required(self):del self.spec['slides'][0]['communication_goal'];self.reject(self.spec)
    def test_duplicate_slide_id(self):self.spec['slides']*=2;self.reject(self.spec)
    def test_duplicate_block_id(self):self.spec['slides'][0]['blocks']*=2;self.reject(self.spec)
    def test_unknown_slot(self):self.spec['slides'][0]['blocks'][0]['slot']='no-slot';self.reject(self.spec)
    def test_required_slot_not_silently_empty(self):self.spec['slides'][0]['layout']='comparison';self.reject(self.spec)
    def test_capacity_not_silently_truncated(self):
        self.spec['slides'][0]['layout']='hero';self.spec['slides'][0]['blocks'].append({'id':'second','module':'statement','data':{'text':'second'}});self.reject(self.spec)
    def test_slot_assignment_backtracks(self):
        layout={'slots':{'a':{'accepts':['metric','statement'],'min':1,'max':1},'b':{'accepts':['metric'],'min':1,'max':1}}}
        blocks=[{'id':'m','module':'metric'},{'id':'s','module':'statement'}]
        self.assertEqual(assign_slots(layout,blocks)['b'][0]['id'],'m')
    def test_safe_identifiers(self):
        for value in ['../secret','a" onclick="x','x/y','Hello','']:
            with self.subTest(value=value),self.assertRaises(ContractError):identifier(value,'id')
    def test_html_escaping(self):
        self.spec['slides'][0]['blocks'][0]['data']['text']='<script>alert(1)</script>'
        html,_=build_deck(self.spec,self.registry);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>alert(1)</script>',html)
    def test_json_script_breakout(self):
        self.spec['slides'][0]['communication_goal']='</script><img src=x onerror=alert(1)>'
        html,_=build_deck(self.spec,self.registry);self.assertIn('\\u003c/script\\u003e',html);self.assertNotIn('</script><img',html)
    def test_no_external_runtime_dependencies(self):
        html,_=build_deck(self.spec,self.registry);self.assertNotIn('<script src=',html);self.assertNotIn('<link ',html)
    def test_source_url_safety(self):
        for url in ['javascript:alert(1)','data:text/html,x','https://u:p@example.com','//example.com']:
            with self.subTest(url=url),self.assertRaises(ContractError):safe_url(url)
    def test_source_url_valid(self):self.assertEqual(safe_url('https://example.com/source'),'https://example.com/source')
    def test_motion_missing_target(self):
        self.spec['slides'][0]['motion']=[{'module':'focus','target':'absent','reason':'emphasize'}];self.reject(self.spec)
    def test_motion_missing_reason(self):
        self.spec['slides'][0]['motion']=[{'module':'focus','target':'message','reason':''}];self.reject(self.spec)
    def test_motion_wrong_module(self):
        self.spec['slides'][0]['motion']=[{'module':'number-count','target':'message','reason':'emphasize'}];self.reject(self.spec)
    def test_motion_wrong_intent(self):
        self.spec['slides'][0]['intent']='ranking';self.spec['slides'][0]['motion']=[{'module':'focus','target':'message','reason':'emphasize'}];self.reject(self.spec)
    def test_multiple_motion_on_target_rejected(self):
        self.spec['slides'][0]['motion']=[{'module':'focus','target':'message','reason':'emphasize'}]*2;self.reject(self.spec)
    def test_bound_focus_markup(self):
        self.spec['slides'][0]['motion']=[{'module':'focus','target':'message','reason':'emphasize'}]
        html,plan=build_deck(self.spec,self.registry);self.assertIn('data-target="#s-one--message"',html);self.assertEqual(plan['slides'][0]['steps'],1)
    def metric(self,value):
        self.spec['slides'][0]['intent']='kpi';self.spec['slides'][0]['blocks']=[{'id':'number','module':'metric','data':{'label':'Count','value':value}}]
    def test_number_bool_rejected(self):self.metric(True);self.reject(self.spec)
    def test_nan_rejected(self):self.metric(float('nan'));self.reject(self.spec)
    def test_infinity_rejected(self):self.metric(float('inf'));self.reject(self.spec)
    def test_negative_number_supported(self):self.metric(-12.5);html,_=build_deck(self.spec,self.registry);self.assertIn('>-12.5<',html)
    def test_number_count_step(self):
        self.metric(12);self.spec['slides'][0]['motion']=[{'module':'number-count','target':'number','reason':'Change in count'}]
        self.assertEqual(plan_deck(self.spec,self.registry)['slides'][0]['steps'],1)
    def test_number_format(self):self.assertEqual(fmt(1200.5),'1,200.5')
    def test_asset_path_escape(self):
        with self.assertRaises(ContractError):media_data('../anything.png',ROOT)
    def test_missing_asset(self):
        with self.assertRaises(ContractError):media_data('does-not-exist.png',ROOT)
    def test_svg_data_rejected(self):
        with self.assertRaises(ContractError):media_data('data:image/svg+xml;base64,PHN2Zz4=',ROOT)
    def test_signature_mismatch(self):
        with self.assertRaises(ContractError):media_data('data:image/png;base64,'+base64.b64encode(b'not-png').decode(),ROOT)
    def test_local_asset_symlink_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'escape.png').symlink_to(ROOT/'SKILL.md')
            with self.assertRaises(ContractError):media_data('escape.png',root)
    def test_json_nan_loading(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"n":NaN}')
            with self.assertRaises(ContractError):load_spec(p)
    def test_all_presets_compile(self):
        for path in (ROOT/'presets').glob('*.json'):
            with self.subTest(preset=path.name):
                html,plan=build_deck(load_spec(path),self.registry,asset_root=path.parent)
                self.assertEqual(len(plan['slides']),html.count('<section data-slide='))
    def test_showcase_compile(self):
        html,plan=build_deck(load_spec(ROOT/'examples/modular-showcase.json'),self.registry)
        self.assertEqual(len(plan['slides']),12);self.assertIn('data:image/png;base64,',html)
    def test_elementary_history_showcase_compile(self):
        html,plan=build_deck(load_spec(ROOT/'examples/elementary-history-showcase.json'),self.registry)
        self.assertEqual(len(plan['slides']),3)
        self.assertEqual(plan['slides'][2]['steps'],2)
        self.assertIn('layout-character-duel',html)
        self.assertIn('data-map-event',html)
    def test_each_theme_compiles(self):
        for theme in self.registry.list('themes'):
            with self.subTest(theme=theme['id']):
                self.spec['theme']=theme['id'];html,_=build_deck(self.spec,self.registry);self.assertIn('data-theme="'+theme['id']+'"',html)
    def test_theme_does_not_own_palette_tokens(self):
        for theme in self.registry.list('themes'):
            css=self.registry.resource(theme,'theme.css')
            for token in ('--paper:','--ink:','--accent:','--surface:'):
                with self.subTest(theme=theme['id'],token=token):self.assertNotIn(token,css)
    def test_art_direction_css_follows_theme_css(self):
        html,plan=build_deck(self.spec,self.registry)
        self.assertLess(html.index('[data-theme="tech"]'),html.index('body[data-palette="'+plan['styles']['palette']['id']+'"]'))
    def test_each_style_pack_compiles(self):
        for key,family,attr in [('typography','typography','data-typography'),('palette','palettes','data-palette'),('dataviz','dataviz','data-dataviz')]:
            for item in self.registry.list(family):
                with self.subTest(family=family,style=item['id']):
                    self.spec['style']={key:item['id']};html,_=build_deck(self.spec,self.registry)
                    self.assertIn(f'{attr}="{item["id"]}"',html)
    def test_character_callout_requires_provenance_label(self):
        png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlQz58AAAAASUVORK5CYII='
        self.spec['theme']='education'
        self.spec['slides'][0].update(intent='dialogue',layout='character-focus',blocks=[{
          'id':'person','module':'character-callout','data':{'src':png,'alt':'Character illustration','name':'Scholar','role':'Official','speech':'A simplified classroom paraphrase.','speechKind':'paraphrase','speechLabel':'Classroom paraphrase'}
        }],motion=[{'module':'speech-reveal','target':'person','reason':'Reveal the viewpoint after introducing the actor'}])
        html,_=build_deck(self.spec,self.registry)
        self.assertIn('data-speech-kind="paraphrase"',html);self.assertIn('Classroom paraphrase',html)

    def test_route_travel_uses_route_count_for_phases(self):
        png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlQz58AAAAASUVORK5CYII='
        routes=[{'label':'Advance','start':{'label':'A','x':10,'y':80},'end':{'label':'B','x':60,'y':35},'traveler':{'src':png,'alt':'Rider'}},
                {'label':'Retreat','start':{'label':'B','x':60,'y':35},'end':{'label':'C','x':85,'y':20},'arcDirection':'down'}]
        self.spec['theme']='education'
        self.spec['slides'][0].update(intent='route',layout='map-focus',blocks=[{'id':'route','module':'map-route','data':{'src':png,'alt':'Teaching map','routes':routes}}],
          motion=[{'module':'route-travel','target':'route','reason':'Show movement in geographic order'}])
        html,plan=build_deck(self.spec,self.registry)
        self.assertEqual(plan['slides'][0]['steps'],2)
        self.assertEqual(html.count('data-route-item'),2)
        self.assertIn('data-route-traveler',html)

    def test_sequence_phase_count(self):
        self.spec['slides'][0].update(intent='sequence',blocks=[{'id':'steps','module':'timeline','data':{'items':['a','b','c']}}],motion=[{'module':'sequence-step','target':'steps','reason':'Order matters'}])
        self.assertEqual(plan_deck(self.spec,self.registry)['slides'][0]['steps'],3)
    def test_bar_negative_rejected(self):
        self.spec['slides'][0]['blocks']=[{'id':'chart','module':'bar-chart','data':{'label':'X','items':[{'label':'a','value':-1},{'label':'b','value':3}]}}];self.reject(self.spec)
    def test_zero_chart_has_finite_geometry(self):
        self.spec['slides'][0]['blocks']=[{'id':'chart','module':'line-chart','data':{'label':'X','items':[{'label':'a','value':0},{'label':'b','value':0}]}}]
        html,_=build_deck(self.spec,self.registry);self.assertNotIn('nan,',html);self.assertNotIn('inf,',html)
    def test_wrong_font_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.woff2';p.write_bytes(b'wrong')
            with self.assertRaises(ContractError):build_deck(self.spec,self.registry,font=p)

if __name__=='__main__':unittest.main()
