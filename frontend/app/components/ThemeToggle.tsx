"use client";

import { useEffect } from "react";
import { useTheme } from "next-themes";

export default function ThemeToggle() {
	const { theme, setTheme, systemTheme } = useTheme();

	useEffect(() => {
		// ensure theme attribute applied on client mount
		const t = theme === "system" ? systemTheme : theme;
		if (t) document.documentElement.classList.toggle("dark", t === "dark");
	}, [theme, systemTheme]);

	return (
		<button
			onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
			className="p-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-white/80 hover:bg-white/[0.06] transition"
			title="Toggle theme"
		>
			{theme === "dark" ? (
				// sun icon
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
					<circle cx="12" cy="12" r="4" />
					<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
				</svg>
			) : (
				// moon icon
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
					<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
				</svg>
			)}
		</button>
	);
}
