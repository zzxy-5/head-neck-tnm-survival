import { describe, expect, it } from 'vitest'

import { formatFixed, formatMedian, matchingLabel } from './presentation'

describe('survival result formatting', () => {
  it('uses explicit wording for unavailable estimates', () => {
    expect(formatMedian(null, 'en')).toBe('Not reached')
    expect(formatMedian(null, 'zh')).toBe('未达到')
    expect(
      formatFixed({ estimate: null, confidence_interval: null, status: 'not_estimable' }, 'en'),
    ).toEqual({
      value: 'Not estimable',
      interval: 'Follow-up does not reach this horizon',
    })
    expect(
      formatFixed({ estimate: null, confidence_interval: null, status: 'not_estimable' }, 'zh'),
    ).toEqual({
      value: '不可估计',
      interval: '随访时间未达到该时间点',
    })
  })

  it('formats stored estimates and confidence intervals as percentages', () => {
    expect(
      formatFixed(
        {
          estimate: 0.734,
          confidence_interval: [0.701, 0.765],
          status: 'estimable',
        },
        'en',
      ),
    ).toEqual({ value: '73.4%', interval: '95% CI 70.1%-76.5%' })
    expect(formatMedian(36, 'zh')).toBe('36.0 个月')
  })

  it('describes the actual fallback level', () => {
    expect(matchingLabel('site_histology_coarse_age', 'en')).toBe(
      'Broader age band; sex not used',
    )
    expect(matchingLabel('site_histology_tnm', 'zh')).toBe('未使用年龄和性别')
    expect(matchingLabel('site_histology_m', 'en')).toBe('Site, histology, and M category only')
    expect(matchingLabel('site_histology', 'zh')).toBe('仅匹配解剖部位和组织学')
    expect(matchingLabel('no_histology', 'en')).toBe('Histology not used')
    expect(matchingLabel('coarse_age', 'zh')).toBe('未使用组织学；使用更宽的年龄组')
    expect(matchingLabel('site_only', 'zh')).toBe('仅匹配解剖部位')
    expect(matchingLabel('site_only', 'en')).toBe('Site only')
  })

  it.each(['zh', 'en'] as const)('preserves unknown matching levels for %s', (locale) => {
    expect(matchingLabel('unexpected_level', locale)).toBe('unexpected_level')
  })
})
