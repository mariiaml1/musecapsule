/** Derive observed transitions for the current sequential workflow. */
export function getObservedTransitions(
    completedNodes: readonly string[],
    activeNode: string | null,
): Set<string> {
    const path = [...completedNodes];

    if (activeNode !== null) {
        path.push(activeNode);
    }

    const transitions = new Set<string>();

    for (let index = 1; index < path.length; index += 1) {
        transitions.add(`${path[index - 1]}->${path[index]}`);
    }

    return transitions;
}
