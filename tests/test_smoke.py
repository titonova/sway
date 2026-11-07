"""Offline end-to-end smoke tests for generic Sway paths, post states and rendering."""
from __future__ import annotations
import json,os,subprocess,sys,tempfile,unittest,shutil
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
DOC='''# Test Demo Org\nA fictional bakery that sells baked goods. Approved colors navy and cream. No actual customer testimonials.\n'''
HTML='''<!doctype html><html><head><style>*{box-sizing:border-box}body{margin:0;background:#10192b;color:#f6f1e9;font:700 62px Arial;display:flex;align-items:center;justify-content:center;width:320px;height:400px}article{padding:40px}span{color:#d97859}</style></head><body><article>HELLO<br><span>SWAY.</span></article></body></html>'''

class SwaySmoke(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.base=Path(self.t.name)
        for n in ('docs','assets','posts'):(self.base/n).mkdir()
        (self.base/'docs'/'overview.md').write_text(DOC)
        (self.base/'assets'/'README.md').write_text('Assets')
        cfg={'version':1,'organizations':{'sample':{'documents_path':str(self.base/'docs'),
              'assets_path':str(self.base/'assets'),'posts_path':str(self.base/'posts'),
              'brands':{'main':{}},'recommendation_engine':{'enabled':False},'publishing':{'enabled':False}}}}
        self.config=self.base/'config.yaml';self.config.write_text(yaml.safe_dump(cfg))
        self.env=dict(os.environ,SWAY_CONFIG=str(self.config))

    def cli(self,*args,success=True):
        r=subprocess.run([sys.executable,'-m',*args],cwd=ROOT,env=self.env,capture_output=True,text=True,timeout=90)
        if success and r.returncode:self.fail(f'command failed {args}:\nSTDERR {r.stderr}\nSTDOUT {r.stdout}')
        try:out=json.loads(r.stdout)
        except json.JSONDecodeError:self.fail('Non-JSON output: '+r.stdout+' STDERR '+r.stderr)
        return r.returncode,out

    def test_documents_and_no_engine(self):
        _,x=self.cli('tools.documents.list_docs','--org','sample')
        self.assertEqual(x['documents'][0]['id'],'overview.md')
        _,x=self.cli('tools.documents.read_docs','--org','sample','overview.md')
        self.assertIn('fictional bakery',x['documents'][0]['content'])
        _,x=self.cli('tools.recommendations.next_post','--org','sample','--brand','main')
        self.assertFalse(x['configured'])
        _,x=self.cli('tools.documents.read_docs','--org','sample','../config.yaml',success=False)
        self.assertFalse(x['ok'])

    def test_document_access_policy_in_smoke(self):
        (self.base/'docs'/'secret.txt').write_text('super confidential')
        cfg=yaml.safe_load(self.config.read_text(encoding='utf-8'))
        cfg['organizations']['sample']['document_access']={
            'allow': ['*.md'],
            'deny': ['private*']
        }
        self.config.write_text(yaml.safe_dump(cfg))
        _,x=self.cli('tools.documents.list_docs','--org','sample')
        doc_ids=[d['id'] for d in x['documents']]
        self.assertIn('overview.md',doc_ids)
        self.assertNotIn('secret.txt',doc_ids)
        _,x=self.cli('tools.documents.read_docs','--org','sample','secret.txt',success=False)
        self.assertFalse(x['ok'])
        self.assertIn('denied by policy',x['error'])

    def test_posts_versions_highlights_and_approval_safety(self):
        _,x=self.cli('tools.posts.manage','create','--org','sample','--brand','main','--post','my_test')
        post=Path(x['path']);v=post/'versions'/'v001'
        (v/'source'/'index.html').write_text(HTML)
        (v/'caption.md').write_text('A real caption for a test, not an actual advertisement.')
        _,x=self.cli('tools.publishing.publish','--org','sample','--post','my_test','--channel','instagram','--dry-run',success=False)
        self.assertIn('not been explicitly approved',x['error'])
        _,x=self.cli('tools.posts.approve','--org','sample','--post','my_test','--channels','instagram',success=False)
        self.assertIn('interactive human TTY',x['error'])
        _,x=self.cli('tools.posts.manage','major-version','--org','sample','--post','my_test')
        self.assertEqual(x['current_version'],'v002')
        self.assertTrue((post/'versions'/'v001'/'source'/'index.html').exists())
        _,x=self.cli('tools.posts.manage','highlight','--org','sample','--post','my_test','--note','good reference','--tags','design')
        _,x=self.cli('tools.posts.highlights','--org','sample','--tag','design')
        self.assertEqual(x['count'],1)

    def test_hash_approval_and_minor_edits(self):
        import src.config as configuration
        from src.posts import approve_record,check_approval
        old_config_path=configuration.CONFIG_PATH
        configuration.CONFIG_PATH=self.config
        _,x=self.cli('tools.posts.manage','create','--org','sample','--brand','main','--post','hash_test')
        folder=Path(x['path'])/'versions'/'v001'
        (folder/'source'/'index.html').write_text(HTML)
        (folder/'output'/'index.png').write_bytes(b'demo-rendered-png-bytes')
        (folder/'caption.md').write_text('Sample reviewed caption.')
        # Test calls the underlying contract directly. Real approval CLI REQUIRES a human TTY.
        try:
            state=approve_record('sample','hash_test',['instagram'],None)
            self.assertEqual(state['current_version'],'v001')
            check_approval('sample','hash_test','instagram',None)
            with self.assertRaisesRegex(Exception,'destination'):check_approval('sample','hash_test','facebook',None)
            (folder/'source'/'index.html').write_text(HTML+'<!-- minor edit, no version -->')
            self.assertTrue(folder.is_dir())
            with self.assertRaisesRegex(Exception,'modified'):check_approval('sample','hash_test','instagram',None)
        finally:
            configuration.CONFIG_PATH=old_config_path

    def test_asset_catalog_and_search(self):
        asset=self.base/'assets'/'logo.svg';asset.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        _,x=self.cli('tools.assets.catalog','add','--org','sample','--path','logo.svg','--caption','Illustrative test logo','--approved','--tags','logo,brand')
        self.assertTrue(x['asset']['approved'])
        _,x=self.cli('tools.assets.search','--org','sample','--query','logo')
        self.assertEqual(x['results'][0]['path'],'logo.svg')
        _,x=self.cli('tools.assets.search','--org','sample','--full-catalog')
        self.assertEqual(x['results'][0]['path'],'logo.svg')

    @unittest.skipUnless(__import__('src.browser', fromlist=['find_browser_executable']).find_browser_executable() is not None, 'No local Chromium')
    def test_real_image_render(self):
        _,x=self.cli('tools.posts.manage','create','--org','sample','--brand','main','--post','image_test')
        d=Path(x['path'])/'versions'/'v001'
        (d/'source'/'index.html').write_text(HTML)
        _,x=self.cli('tools.rendering.render_images','--org','sample','--post','image_test','--width','320','--height','400')
        from PIL import Image
        pic=d/'output'/'index.png';self.assertTrue(pic.exists())
        with Image.open(pic) as im:
            self.assertEqual(im.size,(320,400))

    @unittest.skipUnless(__import__('src.browser', fromlist=['find_browser_executable']).find_browser_executable() is not None and __import__('tools.rendering.render_video', fromlist=['find_ffmpeg_executable']).find_ffmpeg_executable() is not None, 'No Chromium/FFmpeg')
    def test_real_video_render(self):
        _,x=self.cli('tools.posts.manage','create','--org','sample','--brand','main','--post','video_test')
        d=Path(x['path'])/'versions'/'v001'
        (d/'source'/'video.html').write_text(HTML)
        _,x=self.cli('tools.rendering.render_video','--org','sample','--post','video_test','--duration','0.5','--fps','4','--width','320','--height','400')
        self.assertTrue((d/'output'/'video.mp4').stat().st_size>1500)
        self.assertTrue(x['render']['preview_frames'])

if __name__=='__main__':unittest.main()
