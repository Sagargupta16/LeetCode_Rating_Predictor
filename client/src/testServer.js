import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const handlers = [
  http.get("http://localhost:8000/api/contestData", () => {
    return HttpResponse.json({ contests: ["weekly-contest-377"] });
  }),

  http.post("http://localhost:8000/api/predict", () => {
    return HttpResponse.json([
      {
        contest_name: "weekly-contest-377",
        prediction: 25.5,
        rating_before_contest: 1800,
        rank: 1500,
        total_participants: 8000,
        rating_after_contest: 1825.5,
        attended_contests_count: 45,
      },
    ]);
  }),
];

export const server = setupServer(...handlers);
