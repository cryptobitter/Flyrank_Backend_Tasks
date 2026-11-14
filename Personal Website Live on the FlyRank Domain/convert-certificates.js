/**
 * convert-certificates.js
 * Converts certificates from assets/certificates-src/ (PNG, JPG, JPEG, PDF)
 * into optimized WebP images (max width: 1600px, size: < 150 KB)
 * saved to assets/certificates/[slug].webp
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
let sharp;
try {
  sharp = require('sharp');
} catch (e) {
  // sharp not found, will rely on python fallback
}

const SRC_DIR = path.join(__dirname, 'assets', 'certificates-src');
const OUT_DIR = path.join(__dirname, 'assets', 'certificates');

const SLUGS = [
  'flyrank-backend-ai-engineering',
  'flyrank-ai-fluency',
  'walmart-forage',
  'ibm-data-analysis-python',
  'anthropic-claude-101',
  'anthropic-ai-fluency',
  'gdgoc-psit',
  'buildwithbharat-2',
  'bbd-hackathon'
];

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function findSourceFile(slug) {
  if (!fs.existsSync(SRC_DIR)) return null;
  const files = fs.readdirSync(SRC_DIR);
  
  // Exact match with extension
  const extensions = ['.png', '.jpg', '.jpeg', '.webp', '.pdf'];
  for (const ext of extensions) {
    const directMatch = `${slug}${ext}`;
    if (files.includes(directMatch)) {
      return path.join(SRC_DIR, directMatch);
    }
  }

  // Prefix match (in case user named it slug-something.ext)
  const matched = files.find(f => {
    const base = path.parse(f).name.toLowerCase();
    return base.startsWith(slug.toLowerCase()) || slug.toLowerCase().startsWith(base);
  });

  return matched ? path.join(SRC_DIR, matched) : null;
}

async function convertImageWithSharp(inputPath, outputPath) {
  let quality = 82;
  let buffer = await sharp(inputPath)
    .resize({ width: 1600, withoutEnlargement: true })
    .webp({ quality })
    .toBuffer();

  // Ensure size is under 150 KB (153,600 bytes)
  while (buffer.length > 150 * 1024 && quality > 40) {
    quality -= 10;
    buffer = await sharp(inputPath)
      .resize({ width: 1600, withoutEnlargement: true })
      .webp({ quality })
      .toBuffer();
  }

  fs.writeFileSync(outputPath, buffer);
  return buffer.length;
}

function convertWithPythonFallback(inputPath, outputPath) {
  const pyCode = `
import sys, os, io
from PIL import Image

input_path = sys.argv[1]
output_path = sys.argv[2]
ext = os.path.splitext(input_path)[1].lower()

if ext == ".pdf":
    import fitz
    doc = fitz.open(input_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
else:
    img = Image.open(input_path).convert("RGB")

if img.width > 1600:
    new_h = int(img.height * (1600.0 / img.width))
    img = img.resize((1600, new_h), Image.Resampling.LANCZOS)

quality = 82
while quality >= 35:
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality)
    val = buf.getvalue()
    if len(val) <= 150 * 1024 or quality <= 40:
        with open(output_path, "wb") as f:
            f.write(val)
        print(f"SIZE:{len(val)}")
        break
    quality -= 6
`;

  const { spawnSync } = require('child_process');
  const res = spawnSync('python', ['-c', pyCode, inputPath, outputPath], { encoding: 'utf8' });
  if (res.error) throw res.error;
  if (res.status !== 0) {
    throw new Error(res.stderr || res.stdout || 'Python conversion failed');
  }
  const match = res.stdout.match(/SIZE:(\d+)/);
  return match ? parseInt(match[1], 10) : fs.statSync(outputPath).size;
}

async function processAll() {
  console.log('--- Certificate WebP Converter ---');
  console.log(`Source dir: ${SRC_DIR}`);
  console.log(`Output dir: ${OUT_DIR}`);
  console.log('');

  const summary = {
    converted: [],
    missing: []
  };

  for (const slug of SLUGS) {
    const srcFile = findSourceFile(slug);
    const outFile = path.join(OUT_DIR, `${slug}.webp`);

    if (!srcFile) {
      summary.missing.push(slug);
      console.log(`⚠️  [MISSING] ${slug}: No source file found in assets/certificates-src/`);
      // If an old webp exists from a missing slug, remove or keep? We keep it clean
      continue;
    }

    const ext = path.extname(srcFile).toLowerCase();
    try {
      let finalBytes = 0;
      if (ext === '.pdf') {
        finalBytes = convertWithPythonFallback(srcFile, outFile);
      } else {
        if (sharp) {
          finalBytes = await convertImageWithSharp(srcFile, outFile);
        } else {
          finalBytes = convertWithPythonFallback(srcFile, outFile);
        }
      }

      const kb = (finalBytes / 1024).toFixed(1);
      summary.converted.push({ slug, file: path.basename(srcFile), sizeKb: kb });
      console.log(`✅ [CONVERTED] ${slug} <- ${path.basename(srcFile)} (${kb} KB)`);
    } catch (err) {
      console.error(`❌ [ERROR] Failed to convert ${slug}:`, err.message);
      summary.missing.push(slug);
    }
  }

  console.log('\n--- Conversion Summary ---');
  console.log(`Total Slugs: ${SLUGS.length}`);
  console.log(`Successfully Converted: ${summary.converted.length}`);
  console.log(`Missing Image Sources: ${summary.missing.length}`);
  if (summary.missing.length > 0) {
    console.log('Missing slugs:', summary.missing.join(', '));
  }
}

if (require.main === module) {
  processAll().catch(err => {
    console.error('Fatal execution error:', err);
    process.exit(1);
  });
}

module.exports = { processAll, SLUGS };
