import type { FixedEstimate } from './types'
import type { Locale } from './i18n'

export interface FormattedFixedEstimate {
  value: string
  interval: string
}

const matchingLabels: Record<Locale, Record<string, string>> = {
  en: {
    full: 'Exact match',
    no_sex: 'Sex not used',
    site_histology_coarse_age: 'Broader age band; sex not used',
    site_histology_tnm: 'Age and sex not used',
    site_histology_m: 'Site, histology, and M category only',
    site_histology: 'Site and histology only',
    no_histology: 'Histology not used',
    coarse_age: 'Histology not used; broader age band',
    site_tnm: 'Site and TNM only',
    site_m: 'Site and M category only',
    site_only: 'Site only',
  },
  zh: {
    full: '精确匹配',
    no_sex: '未使用性别',
    site_histology_coarse_age: '使用更宽的年龄组；未使用性别',
    site_histology_tnm: '未使用年龄和性别',
    site_histology_m: '仅匹配解剖部位、组织学和 M 分类',
    site_histology: '仅匹配解剖部位和组织学',
    no_histology: '未使用组织学',
    coarse_age: '未使用组织学；使用更宽的年龄组',
    site_tnm: '仅匹配解剖部位和 TNM',
    site_m: '仅匹配解剖部位和 M 分类',
    site_only: '仅匹配解剖部位',
  },
}

export function formatMedian(months: number | null, locale: Locale = 'en'): string {
  if (months === null) {
    return locale === 'zh' ? '未达到' : 'Not reached'
  }

  return locale === 'zh' ? `${months.toFixed(1)} 个月` : `${months.toFixed(1)} months`
}

export function formatFixed(
  estimate: FixedEstimate,
  locale: Locale = 'en',
): FormattedFixedEstimate {
  if (
    estimate.status === 'not_estimable' ||
    estimate.estimate === null ||
    estimate.confidence_interval === null
  ) {
    return {
      value: locale === 'zh' ? '不可估计' : 'Not estimable',
      interval: locale === 'zh' ? '随访时间未达到该时间点' : 'Follow-up does not reach this horizon',
    }
  }

  const [lower, upper] = estimate.confidence_interval
  return {
    value: `${(estimate.estimate * 100).toFixed(1)}%`,
    interval: locale === 'zh'
      ? `95% 置信区间 ${(lower * 100).toFixed(1)}%-${(upper * 100).toFixed(1)}%`
      : `95% CI ${(lower * 100).toFixed(1)}%-${(upper * 100).toFixed(1)}%`,
  }
}

export function matchingLabel(level: string, locale: Locale = 'en'): string {
  return matchingLabels[locale][level] ?? level
}
