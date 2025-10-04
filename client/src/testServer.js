import { rest } from 'msw'
import { setupServer } from 'msw/node'

const handlers = [
  rest.get('http://localhost:8000/api/contestData', (req, res, ctx) => {
    return res(ctx.json({ contests: ['weekly-contest-377'] }))
  }),

  rest.post('http://localhost:8000/api/predict', (req, res, ctx) => {
    return res(
      ctx.json([
        {
          contest_name: 'weekly-contest-377',
          prediction: 25.5,
          rating_before_contest: 1800,
          rank: 1500,
          total_participants: 8000,
          rating_after_contest: 1825.5,
          attended_contests_count: 45,
        },
      ])
    )
  }),
]

export const server = setupServer(...handlers)
