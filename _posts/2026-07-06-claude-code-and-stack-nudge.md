---
layout: post
title: "Coding with AI and making it work for me"
date: 2026-07-06 22:30:00 +0000
categories: ai-tools
---

When I started using AI to help with code, it was copy pasting into ChatGPT's chat interface and going round in circles until I had reduced the problem to the more intricate parts and the scope was small. I spent a lot of time drawing diagrams on a pixel tablet, or notebooks, describing features and scribbling architecture. 

Now, a bunch of AI tooling has redefined my processes. I use Claude Code (CC), AGY or Codex, predominately Claude though. I was skeptical from the start and didn't jump on the CC bandwagon as soon as I could, I still quite liked my copy paste flow with ChatGPT - and I think that was because I still felt in control - once I started using CC completely... well it became my main interface with the code. 

Over the past 6 months I've gone from deriding those who used `--dangerously-skip-permissions` to always running in caffeinated `auto mode`, running between 5 and 20 sessions across all three agents. This kind of just evolved naturally as I changed how I worked as I grew more confident in the model's ability to perform what I needed from the instructions that I would give. 

This led to a new problem, how do I keep track of all these different sessions? Short of a continuous alt-tab across VS Code windows to see which agent needed my attention next, I started thinking about what could fill this gap.

## How I actually run it

In my setup I default to Opus with the 1M-context window, `always-thinking` turned on, and the effort level pinned to `xhigh`. More often than not, that's gonna be needed. The StackOne architecture is across about 6 core repos with many others in the wings. 

At the beginning I was reading and reacting to every single event, can I look at this file? can I do this grep? Now, I use a `SessionStart` hook that `caffeinates` the session, so if Claude has a job on, my Mac won't sleep. Now I set an agent on a task and let it do its thing.

Despite StackOne not running a monorepo, that's how I treat the codebase, I have a root dir `./stackone` that contains all of the business's repos and from there is where I orchestrate my boys (as I call them), but that's the difference now - many agents working across the codebase like science fiction worker robots that can build a science fiction thing in no time at all. 

A few other things that are now part of the furniture:

* **Moved from VS Code to Zed:** Lighter weight experience - I still made it look and feel like VS Code though.
* **iTerm2 for terminal:** I don't run Claude Code in Zed, mainly due to one of its flaws - but more on that later 
* **More than one session at a time:** Different branches, different tickets, different windows. I start the week getting a bunch of agents to pull all the tickets I have assigned and start planning
* **Claude doesn't commit:** I don't let em (well ok sometimes) - mostly because this is the part where I actually review the code manual style
* **MCPs for work systems:** Linear, Datadog, Fireflies - helps Claude plan, check that meeting we had where we discussed a key architectural constraint, check datadog logs after deployment
* **`deep-dive`:**, an internal multi-agent audit plugin, which I've pointed at my own code more than once (more on that below).
* Plus `spark`, `introspect`, `plugin-dev` and a Swift LSP, and an MCP server wired up so the agent can actually call our own APIs rather than guess at them.

I've enjoyed how this setup has evolved. But it has one obvious hole.

## The hole

The exact moment you step away is the moment ya boys hit a blocker.

You kick off three sessions, go make a coffee, and come back to find one of them hit a permission prompt ninety seconds after you left and has been sitting there ever since. Or worse - it *finished*, cleanly, and has just been idle for twenty minutes while you assumed it was still working. The whole "set it going and leave" workflow quietly falls apart if leaving means you don't know when to come back.

And really it's not often I've left the seat, it's just I'm working on something else, maybe I'm in a meeting, or planning with another agent.

## The thing that calls me back

That gap is the entire reason [Stack Nudge](https://github.com/StackOneHQ/stack-nudge) exists. I had been messing around with [Kokoro-82M](https://github.com/hexgrad/kokoro) local text-to-speech (TTS) model - an evolution of using the native macOS TTS and simple hooks to tell me when Claude was done - and made [StackVox](https://github.com/StackOneHQ/stackvox) a little Python wrapper that allowed me to level up my hooks with its awesome TTS. I told the team about StackVox and my colleague Hisku mentioned they had started stack-nudge to fill the same gap - push notifications when Claude was done. They started it back in April; I've been the other main pair of hands on it since.

It's a small macOS app that watches your coding agents and pings you - a banner and a sound, and a bunch of TTS lines if you want - the moment a turn finishes or the agent pauses for approval. Click the banner or navigate through the app UI and it focuses the *exact* window that fired it, even the specific terminal pane inside your editor (compat dependent). You can approve the permission right from its panel without hunting for the right tab.

The nice part is that I'm not testing this on some contrived setup - it's hooked straight into my own Claude Code `Stop` and `PermissionRequest` hooks. I use it all day, which means me and Hisku often tweak and polish it on the fly too.

And the bits I've ended up building map almost one-to-one onto my own annoyances:

* **A keyboard-driven panel:**, because I don't want to reach for the mouse to approve something. Summon it with a hotkey, move around with the arrow keys, approve or focus with Enter.
* **Live session tracking:** - it reads Claude Code's per-process sidecar to show which of my sessions are busy versus idle, and how full each one's context window is, without waiting for a hook to fire.
* **Token accounting per ticket:** A tab that rolls every session up by ticket (guessed from the branch name), showing tokens spent, files changed, and where the work actually got to: *needs-review → committed → pushed → merged*, with real GitHub PR and CI status if you link it.
* **Context-fill alerts:** - a nudge like *"context filling up on `classifier-evolution-2` at 175K, consider `/compact`"* so a session doesn't silently run itself into a wall.
* **Quota tracking:** - the same numbers `claude /usage` prints, but always on screen, with a warning before I sink the weekly cap.

There's also a security and correctness hardening pass in there that I'm quietly proud of, mostly because of *how* it happened: I pointed `deep-dive` - one of the plugins I mentioned earlier - at our own codebase, and then spent a good while working through what it turned up. Things like parsing our phrase files as plain data instead of `eval`-ing them, and hardening the notify script against injection. I made `deep-dive` to help the less-technical members of the team get quick feedback on their projects, focusing on security and completeness of functionality but also to be a tool suitable for auditing production code.

## The bit I like

It supports Cursor, Codex and the AGY too, but Claude Code is the one I live in, so that's where my attention goes. It works best on terminals and IDEs that report their internal pane IDs so we can call them correctly when focusing from the event, I always used iTerm2, but it also excels here - it can take you not only to the correct tab, but the pane within that tab. Like I mentioned earlier, Zed doesn't yet support this, which makes it trickier to use effectively with stack-nudge. 

Mostly I like the symmetry of it. The tool I lean on Claude Code to build is a tool for using Claude Code - and building it *with* the exact workflow it's meant to patch is the fastest way I've found to notice what's still broken. It's open source (MIT) if you want to poke at it: [github.com/StackOneHQ/stack-nudge](https://github.com/StackOneHQ/stack-nudge).
