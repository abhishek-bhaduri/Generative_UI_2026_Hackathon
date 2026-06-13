import { Plus_Jakarta_Sans, Spline_Sans_Mono } from "next/font/google";
import "@copilotkit/react-ui/v2/styles.css";
import "@/a2ui/theme.css";
import "./rfp-cockpit.css";
import { RFPProviders } from "@/components/rfp-intake/Providers";

const plusJakarta = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
  display: "swap",
});

const splineMono = Spline_Sans_Mono({
  variable: "--font-spline-mono",
  subsets: ["latin"],
  display: "swap",
});

export default function RFPLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <RFPProviders>
      <div
        className={`rfp-cockpit-root ${plusJakarta.variable} ${splineMono.variable} antialiased min-h-screen flex flex-col`}
      >
        {children}
      </div>
    </RFPProviders>
  );
}
