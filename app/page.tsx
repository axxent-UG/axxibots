import Cockpit from "@/components/cockpit";
import { isDemo } from "@/lib/config";
export const dynamic = "force-dynamic";
export default function Home() {
  return <Cockpit demo={isDemo()} />;
}
