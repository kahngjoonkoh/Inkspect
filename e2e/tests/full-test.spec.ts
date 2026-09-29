import { expect, test, type Page } from '@playwright/test'

// Two responses per card (R = 20, above the CS minimum of 14).
const RESPONSES: Record<number, [string, string]> = {
  1: ['A bat with its wings spread', 'A butterfly'],
  2: ['Two bears touching noses', 'A red butterfly at the bottom'],
  3: ['Two people lifting a basket', 'A red bow tie'],
  4: ['A giant sitting on a stump', 'Big boots'],
  5: ['A butterfly flying', 'Rabbit ears'],
  6: ['An animal skin rug', 'A totem pole'],
  7: ['Two girls looking at each other', 'A rock arch'],
  8: ['Two animals climbing', 'A pretty flower'],
  9: ['Fire and smoke', 'Two witches'],
  10: ['Blue crabs', 'A face with a moustache'],
}

async function drawLasso(page: Page, cx = 0.5, cy = 0.5, rx = 0.3, ry = 0.3) {
  const svg = page.getByTestId('card-canvas')
  const box = await svg.boundingBox()
  if (!box) throw new Error('card canvas has no size')
  const at = (t: number) => ({
    x: box.x + box.width * (cx + rx * Math.cos(t)),
    y: box.y + box.height * (cy + ry * Math.sin(t)),
  })
  const start = at(0)
  await page.mouse.move(start.x, start.y)
  await page.mouse.down()
  for (let i = 1; i <= 36; i++) {
    const p = at((i / 36) * 2 * Math.PI)
    await page.mouse.move(p.x, p.y, { steps: 2 })
  }
  await page.mouse.up()
}

async function dragAround(page: Page, degrees: number) {
  const box = await page.getByTestId('response-card').boundingBox()
  if (!box) throw new Error('card has no size')
  const cx = box.x + box.width / 2
  const cy = box.y + box.height / 2
  const r = Math.min(box.width, box.height) * 0.35
  const at = (deg: number) => ({ x: cx + r * Math.cos((deg * Math.PI) / 180), y: cy + r * Math.sin((deg * Math.PI) / 180) })
  await page.mouse.move(at(0).x, at(0).y)
  await page.mouse.down()
  for (let d = 10; d <= degrees; d += 10) await page.mouse.move(at(d).x, at(d).y)
  await page.mouse.up()
}

test('a full test: 10 cards, inquiry with drawn areas, results with a structural summary', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('consent-checkbox').check()
  await page.getByTestId('start-button').click()
  await expect(page).toHaveURL(/\/test\//)
  await expect(page.getByTestId('phase-label')).toHaveText('response')

  // ---- Response phase
  for (let card = 1; card <= 10; card++) {
    await expect(page.getByTestId('card-number')).toHaveText(String(card))
    if (card === 5) {
      // Turning is never mentioned on the page. A click must not turn the card; a drag
      // around it does, snapping to quarter turns. Drag half a circle: upside down.
      await expect(page.getByText(/turn/i)).toHaveCount(0)
      const cardImage = page.getByTestId('response-card').locator('img')
      await page.getByTestId('response-card').click()
      await expect(cardImage).toHaveAttribute('style', /rotate\(0deg\)/)
      await dragAround(page, 180)
      await expect(cardImage).toHaveAttribute('style', /rotate\(180deg\)/)
    }
    for (const text of RESPONSES[card]) {
      await page.getByTestId('response-input').fill(text)
      await page.getByTestId('add-response').click()
      await expect(page.locator('.response-list')).toContainText(text)
    }
    await page.getByTestId('next-card').click()
  }

  // ---- Inquiry phase
  await expect(page.getByTestId('phase-label')).toHaveText('inquiry')
  const total = 20
  for (let i = 0; i < total; i++) {
    await expect(page.getByText(`Answer ${i + 1} of ${total}`)).toBeVisible()
    await expect(page.getByTestId('card-canvas')).toBeVisible()
    if ((await page.getByTestId('card-number').textContent()) === '5') {
      await expect(page.getByText(/upside down/i)).toBeVisible()
    }
    if (i === 0) {
      await page.getByTestId('whole-card-toggle').check()
    } else {
      await drawLasso(page)
      await expect(page.getByText(/1 area drawn/)).toBeVisible()
      if (i === 1) {
        // Undo and draw a second, different area.
        await page.getByTestId('undo-region').click()
        await expect(page.getByText(/0 areas drawn/)).toBeVisible()
        await drawLasso(page, 0.3, 0.5, 0.15, 0.25)
        await drawLasso(page, 0.7, 0.5, 0.15, 0.25)
        await expect(page.getByText(/2 areas drawn/)).toBeVisible()
      }
    }
    const explanation = i === 15 ? 'It is pretty, the petals are here' : 'The shape of it, here is the head and body'
    await page.getByTestId('inquiry-explanation').fill(explanation)
    // The API reply says whether the examiner asks a CS keyword follow-up.
    const saved = page.waitForResponse((r) => r.request().method() === 'PUT' && r.url().includes('/inquiry'))
    await page.getByTestId('submit-inquiry').click()
    let followup: string | null = (await (await saved).json()).followup
    let asked = 0
    while (followup) {
      expect(++asked).toBeLessThanOrEqual(2)
      await expect(page.getByTestId('examiner-message').last()).toHaveText(followup)
      await page.getByTestId('followup-answer').fill('The colours and the soft edges')
      const answered = page.waitForResponse((r) => r.url().includes('/followups'))
      await page.getByTestId('submit-followup').click()
      followup = (await (await answered).json()).followup
    }
    if (i === 15) expect(asked).toBe(1) // "pretty" is a CS key word
  }

  // ---- Results
  await expect(page).toHaveURL(/\/results\//)
  // Overview tab first: plain-language bands.
  await expect(page.getByTestId('results-overview')).toBeVisible()
  await expect(page.getByTestId('overview-band')).toHaveCount(6)
  await page.getByRole('tab', { name: 'Professional' }).click()
  const summary = page.getByTestId('results-summary')
  await expect(summary).toContainText('Structural Summary')
  await expect(summary).toContainText('EB')
  await expect(page.getByTestId('protocol-table').locator('tbody tr')).toHaveCount(total)
  await expect(page.getByText(/not a (clinical )?diagnosis/i).first()).toBeVisible()
})
