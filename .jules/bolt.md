## 2024-05-23 - [Redundant Calculation in List Rendering]
**Learning:** High-frequency WebSocket updates (10Hz+) can cause redundant calculations in list items even if memoized. Passing pre-calculated visual props (like colors) from the parent map loop prevents children from recalculating the same logic.
**Action:** When mapping over data streams, compute all derived props in the parent loop and pass them down, keeping child components 'dumb' and purely presentational.
