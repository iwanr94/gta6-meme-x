import fs from 'node:fs';
import path from 'node:path';

// Ensure output directory exists
const outputDir = process.env.MAKEFUN_OUTPUT_DIR || '/output';
fs.mkdirSync(outputDir, { recursive: true });

// Read POST.json from repo root
const postPath = path.join(process.cwd(), 'POST.json');
const outputPath = path.join(outputDir, 'POST.json');

const postContent = fs.readFileSync(postPath, 'utf8');
fs.writeFileSync(outputPath, postContent, 'utf8');

console.log(`Copied ${postPath} to ${outputPath}`);