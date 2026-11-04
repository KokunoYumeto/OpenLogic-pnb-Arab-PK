# اوپن لاجک: پنجابی شاہ مکھی ترجمہ

اوپن لاجک پراجیکٹ (The Open Logic Project) دی کتاب *Open Logic Text* دا پنجابی ترجمہ، شاہ مکھی لپی وچ
(`pnb-Arab-PK`)۔ موجودہ ریلیز v0.2.0 وچ سیٹاں (Sets) دا پورا باب اے: ست ماخذ اکائیاں، چھ حصے، تعریفاں، ثبوت تے
مشقاں، EPUB 3 تے دو PDF (نسخ تے نستعلیق) دی شکل وچ۔

[EPUB ڈاؤن لوڈ کرو](https://github.com/KokunoYumeto/OpenLogic-pnb-Arab-PK/releases/download/v0.2.0/OpenLogic-Sets-Punjabi-Shahmukhi-v0.2.0.epub) ·
[ریلیز v0.2.0](https://github.com/KokunoYumeto/OpenLogic-pnb-Arab-PK/releases/tag/v0.2.0)

## ایہہ کیویں بنایا گیا

ترجمہ تے لے آؤٹ AI نے کیتا اے: OpenAI Codex۔ جانچ وی AI ماڈلاں نے کیتی؛ کسے آزاد مادری زبان بولن والے نے ہلے تک
نظرثانی نئیں کیتی۔ اصطلاحاں لئی پنجابی علمی ماخذ تے مغربی پنجابی وکیپیڈیا ویکھے گئے؛ سیٹ تھیوری دیاں بہت ساریاں
اصطلاحاں عارضی نیں تے جتھے رواج ثابت نئیں اوتھے انگریزی لفظ نال دتا گیا اے۔ ہر فیصلہ
`provenance/TERMINOLOGY_REVIEW_LOG.jsonl` تے [ترجمے دے فیصلیاں دے پیکج](provenance/translation-decisions/START_HERE.md)
وچ درج اے؛ ماخذ دیاں درستیاں `provenance/SOURCE_CORRECTIONS.jsonl` وچ نیں۔ پنجابی نثر سجے توں کھبے چلدی اے تے
ریاضی دیاں عبارتاں کھبے توں سجے رہندیاں نیں۔

## صورتحال

722 ماخذ اکائیاں وچوں 74 دا ترجمہ ریپوزیٹری وچ اے۔ دوبارہ جانچ (15 ستمبر 2026) توں بعد OLP-0001 توں OLP-0026
تیکر دا حصہ (سیٹاں، رشتے تے فنکشن) منظور اے؛ اگلا ترجمہ OLP-0027 دی مرمت مکمل ہون تیکر رکیا ہویا اے
([نوٹس](provenance/CANON_REVALIDATION_NOTICE.md))۔ صرف سیٹاں دے باب دا ریڈر تیار اے۔ PDF ٹیگ شدہ نئیں؛ EPUB وچ
MathML تے تِناں ڈایاگراماں دی وضاحت اے۔ غلطیاں ہو سکدیاں نیں۔

## اندر کی اے

- `upstream/`: پوری انگریزی ماخذ کتاب (722 اکائیاں)؛ `translation/`: پنجابی ترجمہ۔
- `reader/`، `tools/`، `fonts/`: ریڈر بنان دا سامان؛ `provenance/`: جانچ تے فیصلیاں دا ریکارڈ۔
- ریلیز v0.2.0: EPUB، نسخ تے نستعلیق PDF، دوبارہ بنان والا ماخذ، QA ثبوت تے SHA-256 فہرستاں؛ پرانی ریلیز v0.1.0
  وی موجود اے۔

ماخذ دی شناخت TeX توں بغیر جانچو، فیر PDF تے EPUB دوبارہ بناؤ:

```powershell
python tools/verify_source_identity.py
python tools/build_sets_reader.py --output-dir output/rebuild --font-dir fonts
pwsh -NoProfile -File tools/build_reader.ps1 -InputDirectory output/rebuild
python tools/build_sets_epub.py --output-dir output/epub-v0.2.0
```

## ماخذ تے کریڈٹ

- [The Open Logic Project](https://openlogicproject.org/) تے اوہدے [حصہ پاون والے](https://openlogicproject.org/people/)؛
  ماخذ: [ریویژن 9620cc73](https://github.com/OpenLogicProject/OpenLogic/tree/9620cc73f9c8e0ad003c514a5d3748f29611c4c0)۔
- [اوپن لاجک ترجمیاں دا مرکز](https://github.com/KokunoYumeto/OpenLogic-translations)۔
- ایہہ سرکاری ایڈیشن نئیں تے اوپن لاجک پراجیکٹ ولوں منظور شدہ نئیں۔

## لائسنس

اوپن لاجک ٹیکسٹ تے ایہہ ترجمہ CC BY 4.0 ہیٹھ نیں؛ فونٹ OFL 1.1 ہیٹھ؛ وکیپیڈیا دے اقتباس CC BY-SA 4.0 ہیٹھ۔
ویکھو [LICENSE.md](LICENSE.md)۔
