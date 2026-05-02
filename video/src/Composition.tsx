import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
} from "remotion";
import { TitleScene } from "./scenes/TitleScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { SolutionScene } from "./scenes/SolutionScene";
import { ArchitectureScene } from "./scenes/ArchitectureScene";
import { DemoScene } from "./scenes/DemoScene";

import { OutroScene } from "./scenes/OutroScene";

export const MainComposition: React.FC = () => {
  return (
    <>
      <Sequence from={0} durationInFrames={120}>
        <TitleScene />
      </Sequence>
      <Sequence from={120} durationInFrames={240}>
        <ProblemScene />
      </Sequence>
      <Sequence from={360} durationInFrames={300}>
        <SolutionScene />
      </Sequence>
      <Sequence from={660} durationInFrames={690}>
        <DemoScene />
      </Sequence>
      <Sequence from={1350} durationInFrames={300}>
        <ArchitectureScene />
      </Sequence>
      <Sequence from={1650} durationInFrames={150}>
        <OutroScene />
      </Sequence>
    </>
  );
};