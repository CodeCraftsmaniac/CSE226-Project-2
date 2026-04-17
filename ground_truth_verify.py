"""
Ground truth from PDF visual inspection + OCR comparison.
Read each PDF image carefully and compare with OCR output.
"""
import sys, json
sys.path.insert(0, r'd:\CSE226 Project 2 Mine\backend')

from ocr_web import WebOCR
from core import resolve_retakes

# ══════════════════════════════════════════════════════════════════════════════
# GROUND TRUTH - Read directly from PDF images
# ══════════════════════════════════════════════════════════════════════════════

# Use (code, semester) tuples as keys to handle retakes properly
PDF1_TRUTH = {
    # Spring 2007
    ('ACT201', 'Spring 2007'): {'grade': 'F',  'credits': 3.0},
    ('ENG102', 'Spring 2007'): {'grade': 'W',  'credits': 3.0},
    ('MIS105', 'Spring 2007'): {'grade': 'C',  'credits': 3.0},
    # Summer 2007
    ('ACT201', 'Summer 2007'): {'grade': 'B+', 'credits': 3.0},
    ('BUS101', 'Summer 2007'): {'grade': 'A-', 'credits': 3.0},
    ('MIS205', 'Summer 2007'): {'grade': 'A-', 'credits': 3.0},
    # Fall 2007
    ('ACT202', 'Fall 2007'): {'grade': 'B-', 'credits': 3.0},
    ('MGT210', 'Fall 2007'): {'grade': 'A',  'credits': 3.0},
    ('MGT314', 'Fall 2007'): {'grade': 'B',  'credits': 3.0},
    # Spring 2008
    ('ECO101', 'Spring 2008'): {'grade': 'B+', 'credits': 3.0},
    ('ECO172', 'Spring 2008'): {'grade': 'A-', 'credits': 3.0},
    ('ENG103', 'Spring 2008'): {'grade': 'B',  'credits': 3.0},
    ('ENG105', 'Spring 2008'): {'grade': 'B',  'credits': 3.0},
    ('MGT368', 'Spring 2008'): {'grade': 'A',  'credits': 3.0},
    ('MKT202', 'Spring 2008'): {'grade': 'A',  'credits': 3.0},
    ('SOC101', 'Spring 2008'): {'grade': 'B+', 'credits': 3.0},
    # Summer 2008
    ('ACT322', 'Summer 2008'): {'grade': 'C+', 'credits': 3.0},
    ('ECO104', 'Summer 2008'): {'grade': 'B+', 'credits': 3.0},
    ('ECO134', 'Summer 2008'): {'grade': 'B-', 'credits': 3.0},
    ('ECO173', 'Summer 2008'): {'grade': 'C-', 'credits': 3.0},
    ('ECO203', 'Summer 2008'): {'grade': 'B',  'credits': 3.0},
    ('ECO204', 'Summer 2008'): {'grade': 'B',  'credits': 3.0},
    ('ECO249', 'Summer 2008'): {'grade': 'A-', 'credits': 3.0},
    ('FIN254', 'Summer 2008'): {'grade': 'B',  'credits': 3.0},
    ('FIN340', 'Summer 2008'): {'grade': 'B+', 'credits': 3.0},
    ('FIN440', 'Summer 2008'): {'grade': 'B+', 'credits': 3.0},
    ('FIN444', 'Summer 2008'): {'grade': 'A',  'credits': 3.0},
    ('FIN464', 'Summer 2008'): {'grade': 'A',  'credits': 3.0},
    ('LAW200', 'Summer 2008'): {'grade': 'B',  'credits': 3.0},
    ('MGT321', 'Summer 2008'): {'grade': 'B',  'credits': 3.0},
    ('MGT351', 'Summer 2008'): {'grade': 'B',  'credits': 3.0},
    ('MGT489', 'Summer 2008'): {'grade': 'B',  'credits': 3.0},
    # Fall 2009
    ('ACT330', 'Fall 2009'): {'grade': 'C',  'credits': 3.0},
    ('BUS251', 'Fall 2009'): {'grade': 'B-', 'credits': 3.0},
    ('ECO317', 'Fall 2009'): {'grade': 'W',  'credits': 3.0},
    ('FIN433', 'Fall 2009'): {'grade': 'B-', 'credits': 3.0},
    ('ENG102', 'Fall 2009'): {'grade': 'C',  'credits': 3.0},
    # Spring 2009
    ('ENV107', 'Spring 2009'): {'grade': 'B-', 'credits': 3.0},
    # Spring 2010
    ('ACT201', 'Spring 2010'): {'grade': 'A-', 'credits': 3.0},
    ('BIO103', 'Spring 2010'): {'grade': 'A',  'credits': 3.0},
    ('BUS401', 'Spring 2010'): {'grade': 'B',  'credits': 3.0},
    ('FIN435', 'Spring 2010'): {'grade': 'B+', 'credits': 3.0},
    ('MIS205', 'Spring 2010'): {'grade': 'A-', 'credits': 3.0},
    # Spring 2011
    ('BUS498', 'Spring 2011'): {'grade': 'B+', 'credits': 3.0},
    ('ECO244', 'Spring 2011'): {'grade': 'C-', 'credits': 3.0},
    ('MGT372', 'Spring 2011'): {'grade': 'C+', 'credits': 3.0},
}

PDF2_TRUTH = {
    # Fall 2009 (1st semester)
    ('CSE115', 'Fall 2009'):  {'grade': 'A-', 'credits': 3.0},
    ('CSE125', 'Fall 2009'):  {'grade': 'A-', 'credits': 3.0},
    ('CSE173', 'Fall 2009'):  {'grade': 'B+', 'credits': 3.0},
    ('CSE251', 'Fall 2009'):  {'grade': 'B+', 'credits': 3.0},
    ('ENG101', 'Fall 2009'):  {'grade': 'B+', 'credits': 3.0},
    ('MAT120', 'Fall 2009'):  {'grade': 'A',  'credits': 3.0},
    ('PHY107', 'Fall 2009'):  {'grade': 'B',  'credits': 3.0},
    # Spring 2010
    ('CSE174', 'Spring 2010'):  {'grade': 'B+', 'credits': 3.0},
    ('CSE214', 'Spring 2010'):  {'grade': 'A-', 'credits': 3.0},
    ('CHE101', 'Spring 2010'):  {'grade': 'C+', 'credits': 3.0},
    ('EEE132', 'Spring 2010'):  {'grade': 'B',  'credits': 3.0},
    ('EEE311', 'Spring 2010'):  {'grade': 'B+', 'credits': 3.0},
    ('EEE342', 'Spring 2010'):  {'grade': 'A',  'credits': 3.0},
    ('EEE363', 'Spring 2010'):  {'grade': 'A-', 'credits': 3.0},
    ('EEE383', 'Spring 2010'):  {'grade': 'C+', 'credits': 3.0},
    ('ENV107', 'Spring 2010'):  {'grade': 'B',  'credits': 3.0},
    ('MAT125', 'Spring 2010'):  {'grade': 'A',  'credits': 3.0},
    # Summer 2010
    ('EEE283', 'Summer 2010'):  {'grade': 'A',  'credits': 3.0},
    ('EEE452', 'Summer 2010'):  {'grade': 'B+', 'credits': 3.0},
    ('EEE461', 'Summer 2010'):  {'grade': 'B+', 'credits': 3.0},
    ('EEE481', 'Summer 2010'):  {'grade': 'A',  'credits': 3.0},
    ('MAT130', 'Summer 2010'):  {'grade': 'C+', 'credits': 3.0},
    ('PHY107', 'Summer 2010'):  {'grade': 'B-', 'credits': 3.0},
    ('POL104', 'Summer 2010'):  {'grade': 'A',  'credits': 3.0},
    # Fall 2010
    ('ACT201', 'Fall 2010'):  {'grade': 'B-', 'credits': 3.0},
    ('EEE232', 'Fall 2010'):  {'grade': 'B',  'credits': 3.0},
    ('EEE241', 'Fall 2010'):  {'grade': 'B+', 'credits': 3.0},
    ('EEE462', 'Fall 2010'):  {'grade': 'A',  'credits': 3.0},
    ('EEE482', 'Fall 2010'):  {'grade': 'A',  'credits': 3.0},
    ('MAT240', 'Fall 2010'):  {'grade': 'B+', 'credits': 3.0},
    ('PAD201', 'Fall 2010'):  {'grade': 'B+', 'credits': 3.0},
    # Spring 2011
    ('EEE154', 'Spring 2011'):  {'grade': 'A',  'credits': 1.0},
    ('EEE211', 'Spring 2011'):  {'grade': 'B-', 'credits': 3.0},
    ('EEE221', 'Spring 2011'):  {'grade': 'A-', 'credits': 3.0},
    ('EEE414', 'Spring 2011'):  {'grade': 'A-', 'credits': 3.0},
    ('EEE499', 'Spring 2011'):  {'grade': 'A-', 'credits': 3.0},
    ('MAT250', 'Spring 2011'):  {'grade': 'B',  'credits': 3.0},
    ('MAT361', 'Spring 2011'):  {'grade': 'A-', 'credits': 3.0},
    ('PHY108', 'Spring 2011'):  {'grade': 'B-', 'credits': 3.0},
    # Summer 2011
    ('EEE141', 'Summer 2011'):  {'grade': 'A',  'credits': 3.0},
    ('EEE321', 'Summer 2011'):  {'grade': 'B+', 'credits': 3.0},
    ('EEE336', 'Summer 2011'):  {'grade': 'C-', 'credits': 3.0},
    ('MAT350', 'Summer 2011'):  {'grade': 'B',  'credits': 3.0},
    # Fall 2011
    ('EEE221', 'Fall 2011'):  {'grade': 'D+', 'credits': 3.0},
    ('EEE313', 'Fall 2011'):  {'grade': 'A',  'credits': 3.0},
    ('EEE361', 'Fall 2011'):  {'grade': 'D+', 'credits': 3.0},
    ('EEE362', 'Fall 2011'):  {'grade': 'A',  'credits': 3.0},
    # Spring 2012
    ('EEE111', 'Spring 2012'):  {'grade': 'C+', 'credits': 3.0},
    ('EEE312', 'Spring 2012'):  {'grade': 'A-', 'credits': 3.0},
    ('EEE331', 'Spring 2012'):  {'grade': 'A-', 'credits': 3.0},
    ('EEE332', 'Spring 2012'):  {'grade': 'B',  'credits': 3.0},
    ('ENG102', 'Spring 2012'):  {'grade': 'D',  'credits': 3.0},
    ('ENG105', 'Spring 2012'):  {'grade': 'B-', 'credits': 3.0},
    ('MAT116', 'Spring 2012'):  {'grade': 'B',  'credits': 3.0},
    # Summer 2012
    ('EEE141', 'Summer 2012'):  {'grade': 'C',  'credits': 3.0},
    ('ENG103', 'Summer 2012'):  {'grade': 'C',  'credits': 3.0},
    ('MAT120', 'Summer 2012'):  {'grade': 'A',  'credits': 3.0},
    # Fall 2012
    ('EEE254', 'Fall 2012'):  {'grade': 'C',  'credits': 3.0},
    ('EEE411', 'Fall 2012'):  {'grade': 'A',  'credits': 3.0},
    # Spring 2013
    ('EEE280', 'Spring 2013'):  {'grade': 'B',  'credits': 3.0},
    ('EEE413', 'Spring 2013'):  {'grade': 'A-', 'credits': 3.0},
}


def compare(ocr_courses, truth, label):
    """Compare OCR output against ground truth.
    truth keys are (code, semester) tuples to handle retakes.
    """
    # Build OCR lookup by (code, semester)
    ocr_dict = {}
    for c in ocr_courses:
        key = (c['course_code'], c['semester'])
        ocr_dict[key] = c
    # Also build code-only lookup for finding extras
    ocr_codes = {c['course_code'] for c in ocr_courses}

    print(f"\n{'='*80}")
    print(f"  {label} — OCR vs PDF Ground Truth")
    print(f"{'='*80}")

    matched = 0
    grade_mismatch = 0
    credit_mismatch = 0
    sem_mismatch = 0
    missing = 0

    for (code, sem), truth_data in sorted(truth.items()):
        key = (code, sem)
        if key not in ocr_dict:
            # Try code-only match (semester might differ)
            code_matches = [c for c in ocr_courses if c['course_code'] == code]
            if code_matches:
                ocr = code_matches[0]
                issues = []
                if ocr['grade'] != truth_data['grade']:
                    grade_mismatch += 1
                    issues.append(f"grade: OCR={ocr['grade']} PDF={truth_data['grade']}")
                if abs(ocr['credits'] - truth_data['credits']) > 0.01:
                    credit_mismatch += 1
                    issues.append(f"credits: OCR={ocr['credits']} PDF={truth_data['credits']}")
                if ocr['semester'] != sem:
                    sem_mismatch += 1
                    issues.append(f"sem: OCR={ocr['semester']} PDF={sem}")
                if not issues:
                    matched += 1
                    print(f"  ✓ {code} ({sem}): {ocr['grade']} {ocr['credits']}cr")
                else:
                    print(f"  ✗ {code} ({sem}): {', '.join(issues)}")
            else:
                missing += 1
                print(f"  ✗ {code} ({sem}): MISSING (PDF: {truth_data['grade']}, {truth_data['credits']}cr)")
            continue

        ocr = ocr_dict[key]
        issues = []
        if ocr['grade'] != truth_data['grade']:
            grade_mismatch += 1
            issues.append(f"grade: OCR={ocr['grade']} PDF={truth_data['grade']}")
        if abs(ocr['credits'] - truth_data['credits']) > 0.01:
            credit_mismatch += 1
            issues.append(f"credits: OCR={ocr['credits']} PDF={truth_data['credits']}")

        if not issues:
            matched += 1
            print(f"  ✓ {code} ({sem}): {ocr['grade']} {ocr['credits']}cr")
        else:
            print(f"  ✗ {code} ({sem}): {', '.join(issues)}")

    # Check for extra courses in OCR not in truth
    truth_codes = {code for (code, _) in truth.keys()}
    extra = sorted(ocr_codes - truth_codes)
    if extra:
        print(f"\n  Extra courses in OCR (not in truth): {extra}")

    total = len(truth)
    print(f"\n  Matched: {matched}/{total}")
    print(f"  Grade mismatches: {grade_mismatch}")
    print(f"  Credit mismatches: {credit_mismatch}")
    print(f"  Semester mismatches: {sem_mismatch}")
    print(f"  Missing: {missing}")
    print(f"  Accuracy: {matched}/{total} = {matched/total*100:.1f}%")
    return matched, grade_mismatch, credit_mismatch, sem_mismatch, missing


def run_ocr(path, engine='google_vision'):
    ocr = WebOCR(engine=engine)
    result = ocr.extract(path)
    raw_courses = [{'course_code': c.course_code, 'credits': c.credits, 'grade': c.grade, 'semester': c.semester} for c in result.courses]
    resolved, retake_info = resolve_retakes(raw_courses)
    return raw_courses, resolved, retake_info, result


if __name__ == '__main__':
    # PDF 1 — compare RAW (pre-resolution) courses against ground truth
    raw1, resolved1, retakes1, result1 = run_ocr(r'd:\CSE226 Project 2 Mine\samples\694300494-nsu.pdf')
    m1, g1, c1, s1, mi1 = compare(raw1, PDF1_TRUTH, 'PDF 1: 694300494-nsu.pdf (RAW OCR)')
    print(f"\n  Total credits: {result1.total_credits}, CGPA: {result1.cgpa}")
    print(f"  Retakes: {list(retakes1.keys())}")

    # PDF 2
    raw2, resolved2, retakes2, result2 = run_ocr(r'd:\CSE226 Project 2 Mine\samples\Transcript PDF.pdf')
    m2, g2, c2, s2, mi2 = compare(raw2, PDF2_TRUTH, 'PDF 2: Transcript PDF.pdf (RAW OCR)')
    print(f"\n  Total credits: {result2.total_credits}, CGPA: {result2.cgpa}")
    print(f"  Retakes: {list(retakes2.keys())}")

    # Overall
    total_matched = m1 + m2
    total_courses = len(PDF1_TRUTH) + len(PDF2_TRUTH)
    total_grade_err = g1 + g2
    print(f"\n{'='*80}")
    print(f"  OVERALL: {total_matched}/{total_courses} = {total_matched/total_courses*100:.1f}%")
    print(f"  Grade errors: {total_grade_err}")
    print(f"{'='*80}")
