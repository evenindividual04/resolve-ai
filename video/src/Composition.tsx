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
import { FeaturesScene } from "./scenes/FeaturesScene";
import { OutroScene } from "./scenes/OutroScene";

export const MainComposition: React.FC = () => {
  return (
    <>
      <Sequence from={0} durationInFrames={120}>
        <TitleScene />
      </Sequence>
      <Sequence from={120} durationInFrames={180}>
        <ProblemScene />
      </Sequence>
      <Sequence from={300} durationInFrames={150}>
        <SolutionScene />
      </Sequence>
      <Sequence from={450} durationInFrames={180}>
        <ArchitectureScene />
      </Sequence>
      <Sequence from={630} durationInFrames={120}>
        <FeaturesScene />
      </Sequence>
      <Sequence from={750} durationInFrames={150}>
        <DemoScene />
      </Sequence>
      <Sequence from={900} durationInFrames={120}>
        <OutroScene />
      </Sequence>
    </>
  );
};