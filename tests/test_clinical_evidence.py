"""Pure synthetic assertion regressions; no database, network or external model."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

def isolation(event, args):
    if event.startswith('socket.') or event in {'sqlite3.connect', 'subprocess.Popen', 'os.system'}:
        raise RuntimeError('Pure offline evidence fixture')
sys.addaudithook(isolation)
from feature_engine import extract_features
from orchestrator import run_agent
from dynamic_consult import run_dynamic_consult


class EvidenceTests(unittest.TestCase):
    def test_explicit_negative(self):
        for animal in ['犬', '猫']:
            for phrase in ['未见黑便', '没有黑便', '否认黑便', '无黑便', '无明显黑便', '犬无黑便', 'no melena', '未见呕吐、腹泻', '没有抽搐', '未见呼吸困难']:
                with self.subTest(animal=animal, phrase=phrase):
                    f=extract_features(animal+'，'+phrase)
                    for key in ['blood','vomiting','diarrhea','neurologic_signs','respiratory_distress']:
                        self.assertFalse(f[key], (phrase,key))
                    self.assertNotEqual(run_agent(animal+'，'+phrase)['risk_level'], '高')

    def test_question_labels_never_become_findings(self):
        for animal in ['犬','猫']:
            for answer in ['没有','不清楚','','未观察','有']:
                with self.subTest(animal=animal, answer=answer):
                    r=run_dynamic_consult(animal+'，常规体检',[{'question':'是否有黑便或干呕、腹胀？','answer':answer}])
                    self.assertEqual(r['risk_level'],'待核对')
                    self.assertEqual(r['diseases']['diseases'],[])

    def test_yes_to_single_question_is_supported(self):
        r=run_dynamic_consult('犬',[{'question':'是否有黑便？','answer':'有'}])
        self.assertEqual(r['risk_level'],'高')
        self.assertIn('胃肠道出血',r['diseases']['diseases'])

    def test_single_respiratory_yes_preserves_red_flag(self):
        for q in ['是否有呼吸困难？','是否张口呼吸？']:
            r=run_dynamic_consult('犬',[{'question':q,'answer':'有'}])
            self.assertEqual(r['risk_level'],'高')

    def test_positive_answer_does_not_adopt_other_question_symptoms(self):
        r=run_dynamic_consult('犬',[{'question':'是否有黑便或干呕、腹胀？','answer':'有黑便，未见腹胀'}])
        self.assertEqual(r['risk_level'],'高')
        self.assertFalse(any('扭转' in d for d in r['diseases']['diseases']))

    def test_existing_positive_red_flags_preserved(self):
        for text,key in [('犬，今天黑便','blood'),('犬，干呕且腹胀','dog_gdv_risk'),('猫，没有尿','anuria'),('公猫，尿不出来','cat_urinary_obstruction_risk'),('犬，张口呼吸','respiratory_distress'),('犬，抽搐','neurologic_signs'),('犬，不吃','anorexia'),('犬，没精神','low_energy')]:
            with self.subTest(text=text):
                self.assertTrue(extract_features(text)[key])
                if key not in {'anorexia','low_energy'}:self.assertEqual(run_agent(text)['risk_level'],'高')

    def test_positive_signs_with_duration_or_worsening_are_not_negations(self):
        for text in ['猫，无尿三天','猫，没有尿三天','犬，后肢无力加重']:
            self.assertEqual(run_agent(text)['risk_level'],'高',text)
        for text in ['猫，没有尿闭','猫，无尿道阻塞','犬，未见后肢无力加重']:
            self.assertNotEqual(run_agent(text)['risk_level'],'高',text)

    def test_unknown_history_double_negative_and_scope_are_not_normal(self):
        for text in ['犬，是否有黑便','犬，黑便？','犬，黑便吗','犬，不无黑便','犬，不排除黑便','犬，不是没有黑便','犬，既往黑便','犬，没有黑便，呕吐','犬，黑便不清楚','犬，没有黑便且呕吐']:
            with self.subTest(text=text):
                r=run_agent(text)
                self.assertEqual(r['risk_level'],'待核对')
                self.assertTrue(r['input_evidence']['needs_review'])
                self.assertFalse(any('胃肠道出血'==d for d in r['diseases']['diseases']))

    def test_negation_does_not_hide_contrast_positive(self):
        f=extract_features('犬，没有黑便但有呕吐')
        self.assertFalse(f['blood']);self.assertTrue(f['vomiting'])

    def test_conflicts_remain_high_and_visible(self):
        r=run_dynamic_consult('犬，今天黑便',[{'question':'是否有黑便？','answer':'没有'}])
        self.assertEqual(r['risk_level'],'高')
        self.assertIn('blood',r['input_evidence']['conflicts'])
        self.assertTrue(r['input_evidence']['needs_review'])

    def test_no_species_catalogue_or_default_gi_guess(self):
        for animal in ['犬','猫']:
            for text in ['常规体检','未见黑便','资料待补充']:
                r=run_agent(animal+'，'+text)
                self.assertEqual(r['diseases']['diseases'],[])
                self.assertEqual(r['diseases']['checks'],[])
                self.assertEqual(r['risk_level'],'待核对')

    def test_skin_case_has_only_supported_candidates(self):
        r=run_agent('犬，仅皮肤瘙痒')
        self.assertEqual(r['diseases']['diseases'],['过敏性皮肤病/寄生虫/感染性皮肤病鉴别'])
        self.assertEqual(r['diseases']['evidence'][r['diseases']['diseases'][0]],['pruritus'])

    def test_incidental_words_do_not_trigger_toxin(self):
        for text in ['犬，已消毒','犬，咖啡色呕吐物']:
            self.assertFalse(extract_features(text)['toxin'])
        self.assertTrue(extract_features('犬，咖啡色呕吐物')['blood'])
        self.assertTrue(extract_features('犬喝了咖啡')['toxin'])

    def test_negative_does_not_become_positive_no_urine_sign(self):
        self.assertFalse(extract_features('猫，没有尿闭')['anuria'])

    def test_all_candidates_bound_to_active_features(self):
        for text in ['犬，皮肤瘙痒','犬，干呕且腹胀','猫，无尿','犬，黑便','猫，腹泻','犬，没精神']:
            f=extract_features(text);r=run_agent(text)
            for name in r['diseases']['diseases']:
                keys=r['diseases']['evidence'][name]
                self.assertTrue(keys);self.assertTrue(all(f[k] for k in keys))

    def test_original_whitespace_and_unicode_retained(self):
        raw='犬，未见黑便\n  <literal>🐾  '
        r=run_agent(raw)
        self.assertEqual(r['input_evidence']['records'][0]['raw'],raw)
        self.assertLess(len(str(r)),len(raw)*20+10000)

    def test_exotic_existing_path_not_reclassified(self):
        f=extract_features('兔，一天不吃，无粪')
        self.assertNotIn('input_evidence',f)
        self.assertTrue(f['rabbit_gi_stasis_risk'])


if __name__=='__main__':unittest.main()
