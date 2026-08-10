import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const API = "http://localhost:8000";

// Contest history keyed by username, so tests pick a scenario by the name they
// type rather than by patching handlers at runtime.
const HISTORY = [
  {
    name: "weekly-contest-377",
    title: "Weekly Contest 377",
    rank: 742,
    rating_after: 1825.5,
  },
  {
    name: "biweekly-contest-120",
    title: "Biweekly Contest 120",
    rank: 1310,
    rating_after: 1800.0,
  },
];

const handlers = [
  http.get(`${API}/api/contestData`, () => {
    return HttpResponse.json({ contests: ["weekly-contest-377"] });
  }),

  http.get(`${API}/api/userContests/:username`, ({ params }) => {
    switch (params.username) {
      case "ghost":
        return HttpResponse.json({ detail: "not found" }, { status: 400 });
      case "busy":
        return HttpResponse.json({ detail: "slow down" }, { status: 429 });
      case "newcomer":
        return HttpResponse.json([]);
      default:
        return HttpResponse.json(HISTORY);
    }
  }),

  // Echo one prediction per requested contest so multi-contest flows are
  // exercised realistically. The first entry keeps stable values that the
  // single-contest assertions rely on.
  http.post(`${API}/api/predict`, async ({ request }) => {
    const body = await request.json();
    const contests = body.contests?.length
      ? body.contests
      : [{ name: "weekly-contest-377", rank: 1500 }];

    return HttpResponse.json(
      contests.map((contest, i) => ({
        contest_name: contest.name,
        prediction: i === 0 ? 25.5 : -10.25,
        rating_before_contest: i === 0 ? 1800 : 1825.5,
        rank: i === 0 ? 1500 : 1310,
        total_participants: i === 0 ? 8000 : 7000,
        rating_after_contest: i === 0 ? 1825.5 : 1815.25,
        attended_contests_count: 45 + i,
      })),
    );
  }),
];

export const server = setupServer(...handlers);
