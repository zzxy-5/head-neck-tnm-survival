import { describe, expect, it } from 'vitest'

import { localizeValue, t, visibleCopy } from './i18n'
import options from '../public/data/options.json'

describe('i18n', () => {
  it('provides Chinese and English interface copy', () => {
    expect(t('zh', 'header.eyebrow')).toBe('基于 SEER 数据库的回顾性分析')
    expect(t('zh', 'header.title')).toBe('头颈肿瘤 TNM 分期分层生存分析')
    expect(t('zh', 'header.notice')).toBe('仅供临床、科研参考')
    expect(t('en', 'header.title')).toBe('TNM Stage-Stratified Survival Analysis of Head and Neck Tumors')
    expect(t('zh', 'filter.eyebrow')).toBe('研究队列构建')
    expect(t('zh', 'filter.heading')).toBe('病例筛选条件')
    expect(t('zh', 'footer')).toBe('登记数据库衍生估计，仅供临床、科研参考。')
    expect(t('zh', 'filter.submit')).toBe('查找可比队列')
    expect(t('en', 'filter.submit')).toBe('Find comparable cohort')
  })

  it.each([
    ['Female', '女性'],
    ['Male', '男性'],
    ['Tongue', '舌'],
    ['Floor of Mouth', '口底'],
    ['Squamous cell carcinoma', '鳞状细胞癌'],
    ['8050-8089: squamous cell neoplasms', '8050-8089：鳞状细胞肿瘤'],
    ['Unknown', '未知'],
    ['Any', '不限'],
    ['Nose, Nasal Cavity and Middle Ear', '鼻腔、中耳及鼻旁窦'],
    ['Larynx', '喉'],
    ['Thyroid', '甲状腺'],
  ])('localizes %s for display only', (raw, translated) => {
    expect(localizeValue('zh', raw)).toBe(translated)
    expect(localizeValue('en', raw)).toBe(raw)
  })

  it.each([
    ['AJCC 7th edition', 'AJCC 第 7 版'],
    ['SEER Combined TNM', 'SEER Combined TNM'],
  ])('localizes supported stage source %s without changing English', (raw, translated) => {
    expect(localizeValue('zh', raw)).toBe(translated)
    expect(localizeValue('en', raw)).toBe(raw)
  })

  it('localizes the TNM-only thymic histology without changing English', () => {
    const raw = '8580-8589: thymic epithelial neoplasms'

    expect(localizeValue('zh', raw)).toBe('8580-8589：胸腺上皮性肿瘤')
    expect(localizeValue('en', raw)).toBe(raw)
  })

  it('has an explicit Chinese label for every real histology option', () => {
    for (const raw of options.histology_groups) {
      const translated = localizeValue('zh', raw)

      expect(translated, `missing explicit Chinese mapping for ${raw}`).not.toBe(raw)
      expect(translated).not.toMatch(/^[0-9]+-[0-9]+:/)
    }
  })

  it('falls back to the raw value', () => {
    expect(localizeValue('zh', 'Unexpected category')).toBe('Unexpected category')
  })

  it('documents the single 2010-2017 TNM cohort and fixed-time confidence intervals', () => {
    const chinese = t('zh', 'method.tnmDescription')
    const english = t('en', 'method.tnmDescription')

    expect(t('zh', 'method.tnmTitle')).toBe('基于TNM分期的Kaplan–Meier生存分析')
    expect(chinese).toBe('本队列纳入2010—2017年诊断的病例。2010—2015年病例采用AJCC第7版T、N和M分期变量，2016—2017年病例采用SEER Combined TNM变量。依据AJCC第7版分期规则，将原始记录中的MX规范化为cM0，并纳入M0组。采用Kaplan–Meier法估计不同T、N和M分期患者的总生存率；报告1年、3年和5年总生存率及其95%置信区间。')
    expect(english).not.toContain('Confidence interval bands')
    expect(english).toContain('2010-2017')
    expect(english).toContain('AJCC 7th edition')
    expect(english).toContain('SEER Combined TNM')
    expect(english).toContain('MX')
    expect(english).toContain('M0')
    expect(english).toContain('95% confidence intervals')
  })

  it.each(['zh', 'en'] as const)('does not advertise Summary Stage or EOD in visible %s copy', (locale) => {
    expect(visibleCopy(locale)).not.toMatch(/Summary Stage|EOD/i)
  })
})
