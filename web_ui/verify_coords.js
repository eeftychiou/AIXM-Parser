const fs = require('fs');
const content = fs.readFileSync('js/aixm-parser.js', 'utf8');
// Mock window and document to load the script
global.window = {};
eval(content);
const parser = new AIXMParser();

const tests = [
    { input: "341200N", expected: 34.2 },
    { input: "0163411E", expected: 16.5697 },
    { input: "510520.60N", expected: 51.08905 },
    { input: "43.7N", expected: 43.7 }
];

tests.forEach(t => {
    const r = parser.parseCoordinate(t.input);
    const ok = Math.abs(r - t.expected) < 0.001;
    console.log(`Input: ${t.input}, Expected: ${t.expected}, Got: ${r}, OK: ${ok}`);
});
