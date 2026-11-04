import assert from "node:assert/strict";
import test from "node:test";
import { groupIdeaVersions, getIdeaFoundation, versionLabel } from "../src/idea-versions.ts";

const idea = (id, parent = null) => ({
  id, previous_idea_id: parent, title: "Same title", description: "A concept",
  goal_alignment: "A goal", image_ids: ["i1"], hypothesis_ids: ["h1"],
});

test("groups chains and branches, even with children before parents", () => {
  const input = [idea("c", "b"), idea("sibling", "a"), idea("b", "a"), idea("a"), idea("unrelated")];
  const before = structuredClone(input);
  const groups = groupIdeaVersions(input);
  assert.equal(groups.length, 2);
  assert.equal(groups[0].root.id, "a");
  assert.deepEqual(groups[0].versions.map((v) => [v.idea.id, v.depth]), [
    ["a", 0], ["sibling", 1], ["b", 1], ["c", 2],
  ]);
  assert.equal(groups[0].versions[1].idea.previous_idea_id, "a");
  assert.equal(groups[0].versions[2].idea.previous_idea_id, "a");
  assert.equal(versionLabel(groups[0], "a"), "Original");
  assert.equal(versionLabel(groups[0], "c"), "Revision 3");
  assert.deepEqual(input, before);
});

test("retains orphan histories without calling the orphan an original", () => {
  const groups = groupIdeaVersions([idea("child", "orphan"), idea("orphan", "missing")]);
  assert.equal(groups[0].issue, "missing_parent");
  assert.deepEqual(groups[0].versions.map((v) => v.idea.id), ["orphan", "child"]);
  assert.equal(versionLabel(groups[0], "orphan"), "Saved version 1");
});

test("keeps every cyclic record visible and terminates", () => {
  const groups = groupIdeaVersions([idea("a", "b"), idea("b", "a"), idea("c", "a")]);
  assert.equal(groups.length, 3);
  assert.ok(groups.every((g) => g.issue === "cycle"));
  assert.deepEqual(groups.flatMap((g) => g.versions.map((v) => v.idea.id)), ["a", "b", "c"]);
  assert.deepEqual(groupIdeaVersions([]), []);
});

test("distinguishes inactive, missing, unlinked and active foundations", () => {
  const session = { images: [{ id: "i1" }], hypotheses: [{ id: "h1", status: "proposed", image_ids: ["i1"] }] };
  assert.equal(getIdeaFoundation(idea("a"), session), "active");
  assert.equal(getIdeaFoundation({ ...idea("a"), hypothesis_ids: [] }, session), "unlinked");
  assert.equal(getIdeaFoundation({ ...idea("a"), hypothesis_ids: ["absent"] }, session), "missing");
  assert.equal(getIdeaFoundation({ ...idea("a"), image_ids: ["absent"] }, session), "missing");
  for (const status of ["unsupported", "superseded"]) {
    assert.equal(getIdeaFoundation(idea("a"), { ...session, hypotheses: [{ ...session.hypotheses[0], status }] }), "inactive");
  }
  assert.equal(getIdeaFoundation(idea("a"), { ...session, hypotheses: [{ id: "h1", status: "supported", image_ids: ["other"] }] }), "missing");
});
