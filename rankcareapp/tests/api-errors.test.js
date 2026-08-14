import test from 'node:test'
import assert from 'node:assert/strict'

import {
  ApiRequestError,
  apiRequest,
  normalizeApiError,
  normalizeValidationErrors,
} from '../src/lib/api.js'

test('maps FastAPI validation details to useful field errors', () => {
  const result = normalizeValidationErrors([
    { loc: ['body', 'mobileNumber'], msg: 'Field required' },
    { loc: ['body', 'email'], msg: 'value is not a valid email address' },
  ])
  assert.equal(result.fieldErrors.mobileNumber, 'Mobile number is required.')
  assert.equal(result.fieldErrors.email, 'Enter a valid email address.')
  assert.match(result.message, /Mobile number is required/)
})

test('normalizes plan, feature, keyword, and payment failures', () => {
  const upgrade = normalizeApiError({ status: 403, responseData: { message: 'blocked', data: { error: 'upgrade_required', upgrade_required: true } } })
  assert.equal(upgrade.upgradeRequired, true)
  assert.equal(upgrade.message, 'This feature is available on paid plans. Upgrade to continue.')

  const limit = normalizeApiError({ status: 429, responseData: { data: { error: 'feature_limit_exceeded', usage: { used: 10, limit: 10, remaining: 0, resetAt: '2026-09-13T00:00:00' } } } })
  assert.equal(limit.message, "You've used 10 of 10 for this billing cycle.")
  assert.equal(limit.remaining, 0)
  assert.equal(limit.resetAt, '2026-09-13T00:00:00')

  assert.equal(normalizeApiError({ status: 409, message: 'Keyword already exists for this project' }).code, 'DUPLICATE_KEYWORD')
  assert.equal(normalizeApiError({ status: 403, message: 'Keyword was recently deleted. Cooldown active.' }).code, 'KEYWORD_READD_COOLDOWN')
  assert.equal(normalizeApiError({ status: 400, message: 'Payment plan mismatch' }).code, 'PAYMENT_PLAN_MISMATCH')
})

test('normalizes expected auth, credit, capacity, and keyword cases', () => {
  const cases = [
    [{ status: 401, code: 'INVALID_CREDENTIALS', message: 'raw' }, 'INVALID_CREDENTIALS', 'Invalid email or password.'],
    [{ status: 403, code: 'EMAIL_VERIFICATION_REQUIRED', message: 'raw' }, 'EMAIL_VERIFICATION_REQUIRED', 'Please verify your email before logging in.'],
    [{ status: 400, code: 'OTP_EXPIRED', message: 'raw' }, 'OTP_EXPIRED', 'The OTP has expired. Please request a new one.'],
    [{ status: 400, code: 'OTP_INVALID', message: 'raw' }, 'OTP_INVALID', 'The OTP is incorrect. Please try again.'],
    [{ status: 402, message: 'Insufficient credits. Required: 20' }, 'INSUFFICIENT_CREDITS', 'You do not have enough spendable credits for this action.'],
    [{ status: 403, message: 'Domain limit reached. Your plan allows 1.' }, 'PROJECT_LIMIT_REACHED', 'Your project limit has been reached. Upgrade to add another project.'],
    [{ status: 403, message: 'Keyword limit reached. Your plan allows 5.' }, 'KEYWORD_LIMIT_REACHED', 'Your keyword limit has been reached.'],
    [{ status: 400, code: 'KEYWORD_INACTIVE', message: 'raw' }, 'KEYWORD_INACTIVE', 'Activate this keyword before refreshing it.'],
  ]
  for (const [input, code, message] of cases) {
    const normalized = normalizeApiError(input)
    assert.equal(normalized.code, code)
    assert.equal(normalized.message, message)
  }
})

test('normalizes network and server failures without exposing internals', () => {
  assert.equal(
    normalizeApiError(new TypeError('Failed to fetch')).message,
    "We couldn't connect to RankCare. Check your connection and try again.",
  )
  assert.equal(
    normalizeApiError({ status: 500, message: 'database password leaked in traceback' }).message,
    'Something went wrong while processing your request. Please try again.',
  )
})

test('login verification rejection remains a catchable normalized API error', async (t) => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({
    success: false,
    message: 'Please verify your mobile number before logging in',
    data: { error: 'MOBILE_VERIFICATION_REQUIRED', action: 'verify_mobile' },
  }), { status: 403, headers: { 'content-type': 'application/json' } })
  t.after(() => { globalThis.fetch = originalFetch })

  await assert.rejects(
    apiRequest('/auth/login', { method: 'POST', body: '{}' }),
    (error) => error instanceof ApiRequestError
      && error.code === 'MOBILE_VERIFICATION_REQUIRED'
      && error.action === 'verify_mobile',
  )
})

test('normalizes a FastAPI 422 response through the real request wrapper', async (t) => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({
    detail: [{ loc: ['body', 'mobileNumber'], msg: 'Field required' }],
  }), { status: 422, headers: { 'content-type': 'application/json' } })
  t.after(() => { globalThis.fetch = originalFetch })

  await assert.rejects(
    apiRequest('/auth/register', { method: 'POST', body: '{}' }),
    (error) => error.fieldErrors.mobileNumber === 'Mobile number is required.'
      && error.message === 'Mobile number is required.',
  )
})

test('keeps structured country-aware mobile validation attached to the registration field', () => {
  const normalized = normalizeApiError({
    status: 422,
    responseData: {
      message: 'Enter a valid mobile number for the selected country.',
      data: {
        error: 'INVALID_MOBILE_NUMBER',
        fieldErrors: { mobile: 'Enter a valid mobile number for the selected country.' },
      },
    },
  })
  assert.equal(normalized.code, 'INVALID_MOBILE_NUMBER')
  assert.equal(normalized.fieldErrors.mobile, 'Enter a valid mobile number for the selected country.')
  assert.equal(normalized.message, 'Enter a valid mobile number for the selected country.')
})

test('authenticated mutations use cookies and CSRF without bearer credentials', async (t) => {
  const originalFetch = globalThis.fetch
  const originalDocument = globalThis.document
  let observed
  globalThis.document = { cookie: 'rankcare_csrf=csrf-value' }
  globalThis.fetch = async (_url, options) => {
    observed = options
    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    })
  }
  t.after(() => {
    globalThis.fetch = originalFetch
    if (originalDocument === undefined) delete globalThis.document
    else globalThis.document = originalDocument
  })

  await apiRequest('/projects', { method: 'POST', body: '{}' })
  assert.equal(observed.credentials, 'include')
  assert.equal(observed.headers['X-CSRF-Token'], 'csrf-value')
  assert.equal(observed.headers.Authorization, undefined)
  assert.equal(observed.headers['X-Session-Token'], undefined)
})
