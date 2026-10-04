import React from "react";
import TestRenderer from "react-test-renderer";
import { test } from "node:test";
import assert from "node:assert/strict";
import ConsultEvidence from "../src/components/ConsultEvidence";

test("legacy results remain readable without invented evidence", () => {
  const view = TestRenderer.create(<ConsultEvidence />);
  assert.equal(view.toJSON(), null); view.unmount();
});
test("unknown and contradictory raw observations remain visible and literal", () => {
  const raw = '  未见黑便\n<script>alert(1)</script>🐾  ';
  const view = TestRenderer.create(<ConsultEvidence evidence={{needs_review:true,conflicts:['blood'],records:[
    {source:'主诉',state:'negative',raw},
    {source:'追问第1轮',state:'unknown',raw:'不清楚',question:'是否有黑便？'},
    {source:'问卷/notes',state:'historical',raw:'以前有黑便'},
  ]}} />);
  const output = JSON.stringify(view.toJSON());
  assert.match(output, /不能视为正常/); assert.match(output, /肯定与否定/);
  assert.match(output, /未知／待核对/); assert.match(output, /时间待核对/);
  assert.equal(view.root.findAllByType('pre')[0].children[0], raw);
  assert.equal(view.root.findAllByType('script').length, 0);
  view.unmount();
});
