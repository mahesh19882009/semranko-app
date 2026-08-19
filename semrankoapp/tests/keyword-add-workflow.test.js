import { describe, it } from 'node:test';
import assert from 'node:assert';

describe('Keyword Add Workflow', () => {
  it('parseKeywords splits by newline and comma', () => {
    const parseKeywords = (text) => {
      return text
        .split(/[\n,]+/)
        .map((kw) => kw.trim())
        .filter((kw) => kw.length > 0);
    };

    assert.deepStrictEqual(parseKeywords('seo\nagency\nharyana'), ['seo', 'agency', 'haryana']);
    assert.deepStrictEqual(parseKeywords('seo, agency, haryana'), ['seo', 'agency', 'haryana']);
    assert.deepStrictEqual(parseKeywords('seo\nagency, haryana'), ['seo', 'agency', 'haryana']);
    assert.deepStrictEqual(parseKeywords('  seo  \n  agency  '), ['seo', 'agency']);
    assert.deepStrictEqual(parseKeywords(''), []);
    assert.deepStrictEqual(parseKeywords('\n\n,'), []);
  });

  it('detects duplicate keywords', () => {
    const keywords = ['seo', 'agency', 'seo', 'haryana', 'agency'];
    const seen = new Set();
    const unique = [];
    for (const kw of keywords) {
      const normalized = kw.toLowerCase();
      if (seen.has(normalized)) continue;
      seen.add(normalized);
      unique.push(kw);
    }
    assert.strictEqual(unique.length, 3);
    assert.deepStrictEqual(unique, ['seo', 'agency', 'haryana']);
  });

  it('calculates duplicate count', () => {
    const parsed = ['seo', 'agency', 'seo', 'haryana', 'agency'];
    const seen = new Set();
    const unique = [];
    for (const kw of parsed) {
      const normalized = kw.toLowerCase();
      if (seen.has(normalized)) continue;
      seen.add(normalized);
      unique.push(kw);
    }
    const duplicateCount = parsed.length - unique.length;
    assert.strictEqual(duplicateCount, 2);
  });

  it('identifies existing keywords', () => {
    const unique = ['seo', 'agency', 'haryana'];
    const tableData = [
      { keyword: 'seo' },
      { keyword: 'marketing' },
    ];
    const existingSet = new Set(tableData.map((r) => r.keyword.toLowerCase()));
    const existing = unique.filter((kw) => existingSet.has(kw.toLowerCase()));
    const newKeywords = unique.filter((kw) => !existingSet.has(kw.toLowerCase()));
    assert.strictEqual(existing.length, 1);
    assert.strictEqual(newKeywords.length, 2);
    assert.deepStrictEqual(existing, ['seo']);
    assert.deepStrictEqual(newKeywords, ['agency', 'haryana']);
  });

  it('calculates projected keyword count', () => {
    const tableDataCount = 42;
    const newKeywordsCount = 10;
    const projectedTotal = tableDataCount + newKeywordsCount;
    assert.strictEqual(projectedTotal, 52);
  });

  it('detects limit exceed', () => {
    const keywordLimit = 100;
    const projectedTotal = 125;
    const wouldExceedLimit = projectedTotal > keywordLimit;
    const wouldExceedBy = projectedTotal - keywordLimit;
    assert.strictEqual(wouldExceedLimit, true);
    assert.strictEqual(wouldExceedBy, 25);
  });

  it('calculates total credit cost', () => {
    const newKeywordsCount = 5;
    const costPerKeyword = 20;
    const totalCost = newKeywordsCount * costPerKeyword;
    assert.strictEqual(totalCost, 100);
  });
});
