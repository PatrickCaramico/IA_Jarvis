import assert from "node:assert/strict";
import test from "node:test";

import { matchLogoUrl, matchSides } from "../src/hooks/useFanMatch.js";

test("escudos e rótulos seguem o Palmeiras como mandante", () => {
  const sides = matchSides({
    home_away: "home",
    opponent: "Remo",
    score: { home: 2, away: 1 },
  });

  assert.equal(sides.home, "Palmeiras");
  assert.equal(sides.away, "Remo");
  assert.equal(sides.homeLogoSide, "ours");
  assert.equal(sides.awayLogoSide, "theirs");
  assert.equal(sides.homeLabel, "MANDANTE");
  assert.equal(sides.awayLabel, "VISITANTE");
});

test("escudos e rótulos seguem o Palmeiras como visitante", () => {
  const sides = matchSides({
    home_away: "away",
    opponent: "Remo",
    score: { home: 1, away: 2 },
  });

  assert.equal(sides.home, "Remo");
  assert.equal(sides.away, "Palmeiras");
  assert.equal(sides.homeLogoSide, "theirs");
  assert.equal(sides.awayLogoSide, "ours");
  assert.equal(sides.homeLabel, "MANDANTE");
  assert.equal(sides.awayLabel, "VISITANTE");
});

test("sem partida, mantém escudo e rótulos do Palmeiras mandante", () => {
  const sides = matchSides(null);

  assert.equal(sides.home, "Palmeiras");
  assert.equal(sides.away, "");
  assert.equal(sides.homeScore, 0);
  assert.equal(sides.awayScore, 0);
  assert.equal(sides.homeLogoSide, "ours");
  assert.equal(sides.awayLogoSide, "theirs");
});

test("versiona a URL do escudo com o ID da partida", () => {
  assert.equal(
    matchLogoUrl({ id: "espn_42" }, "theirs"),
    "/api/fan/logo/theirs?v=espn_42",
  );
});

test("pede o escudo ao backend e leva o token só quando existe", () => {
  assert.equal(
    matchLogoUrl({ id: "espn_42" }, "ours", { base: "http://192.168.0.10:8000" }),
    "http://192.168.0.10:8000/api/fan/logo/ours?v=espn_42",
  );
  assert.equal(
    matchLogoUrl({ id: "espn_42" }, "theirs", { base: "http://192.168.0.10:8000", token: "abc 123" }),
    "http://192.168.0.10:8000/api/fan/logo/theirs?v=espn_42&token=abc+123",
  );
});
