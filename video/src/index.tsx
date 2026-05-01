import { registerRoot } from "remotion";
import { Composition } from "remotion";
import { MainComposition } from "./Composition";

export default function RemotionRoot() {
  return (
    <>
      <Composition
        id="ResolveAI"
        component={MainComposition}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={900}
      />
    </>
  );
}

registerRoot(RemotionRoot);