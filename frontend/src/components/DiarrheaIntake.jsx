import React from "react";
import ChiefComplaintIntake from "./ChiefComplaintIntake";
// Preserve the M7 component API and its exact visible labels.
export default function DiarrheaIntake(props) {
  return <ChiefComplaintIntake {...props} intakeKey={props.intakeKey || "diarrhea"} />;
}
