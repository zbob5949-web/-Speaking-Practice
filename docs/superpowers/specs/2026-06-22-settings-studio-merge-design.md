# Settings Studio Merge Design

## Goal

Simplify the main navigation by removing the standalone Studio entry and merging developer debugging tools into Settings.

## Current Problem

Settings currently displays static AI Model and Input cards plus a Save Settings button, but these controls do not update backend configuration or frontend behavior. Studio contains Prompt Management and Product Flowchart, both of which are configuration/debugging tools and fit better inside Settings than as a primary navigation destination.

## Approved Approach

Use方案 A: fully merge Studio into Settings.

## UX Design

Settings becomes a unified configuration page with three internal sections:

- Learning Goals: keep the existing profile list, switch action, delete action, and create-new-goal action.
- Prompt Management: move the existing Studio prompt list, prompt editor, and save behavior into Settings.
- Product Flowchart: move the existing Studio Mermaid diagram into Settings.

The sidebar navigation becomes:

- Today
- Plan
- Growth
- Settings

The standalone Studio navigation item and `studio` view are removed from App-level routing.

## Behavior

- Prompt editing continues to call the existing `getPrompts()` and `updatePrompt()` APIs.
- Product flowchart rendering continues to use the current Mermaid implementation and flowchart definition.
- Settings no longer shows AI Model, Input, or Save Settings because they do not have functional behavior.
- Existing profile switching, deleting, and onboarding reset behavior remains unchanged.

## Testing

Frontend tests should verify:

- Sidebar no longer shows Studio.
- Settings no longer shows AI Model, Input, or Save Settings.
- Settings shows Prompt 管理 and 产品流程图.
- Prompt editing still loads prompts and calls `updatePrompt()` when saving.

