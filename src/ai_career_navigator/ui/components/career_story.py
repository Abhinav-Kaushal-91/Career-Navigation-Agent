"""Reference-aligned, read-only career story. Styles stay inside a shadow root."""

import re

import pandas as pd
import streamlit as st

STORY_VERSION = "career-story-v2-unknown-zero"

CSS = """
:host{font-family:var(--st-font, 'Source Sans 3', sans-serif);color:#253045;font-size:15px;}
*{box-sizing:border-box} p{margin:0;line-height:1.55}
h4{margin:0 0 8px;font-size:17px;line-height:1.4}
.journey{container-type:inline-size;border:1px solid #dce2ec;border-radius:12px;padding:24px;}
.stages{display:grid;grid-template-columns:repeat(var(--count),minmax(0,1fr));gap:22px;
list-style:none;margin:0;padding:0;}
.stage{position:relative;min-width:0}.stage:not(:last-child):before{content:'';position:absolute;
left:44px;top:21px;width:calc(100% - 22px);height:2px;background:#dce2ec;}
.circle{position:relative;width:42px;height:42px;border-radius:50%;display:grid;place-items:center;
background:#edf2ff;color:#2851d8;font-weight:650;border:1px solid #c5d2f7;}
.stage:first-child .circle{background:#2851d8;color:white;}
.eyebrow{color:#606b7c;font-size:12px;margin:16px 0 6px;
letter-spacing:.04em;text-transform:uppercase;}
.stage h4{font-size:16px;overflow-wrap:anywhere}.stage p{font-size:13px;color:#606b7c;}
button{font:inherit;font-size:13px;color:#2851d8;border:0;background:transparent;padding:10px 0;
cursor:pointer;min-height:44px;text-align:left;}button:focus-visible{outline:2px solid #2851d8;}
button[aria-pressed=true]{text-decoration:underline;text-underline-offset:4px;}
.detail{margin-top:22px;padding:18px 20px;border-left:3px solid #2851d8;background:#f5f7fa;
border-radius:8px;}.detail p{font-size:14px}
.done{margin-top:12px!important;font-size:13px;color:#606b7c;}
.steps{list-style:none;padding:0;margin:0;}.step{display:grid;grid-template-columns:34px 1fr;
gap:16px;position:relative;padding:0 0 26px;}
.step:not(:last-child):before{content:'';position:absolute;
width:2px;left:16px;top:38px;bottom:4px;background:#dce2ec;}
.step .circle{width:34px;height:34px;border:0}.step h4{font-size:16px;margin:3px 0 7px;}
.step p{font-size:15px}.completion{margin-top:12px;background:#f5f7fa;border-radius:8px;
padding:12px 16px;font-size:13px;line-height:1.5;color:#536072;}
@container(max-width:640px){.stages{grid-template-columns:1fr;gap:0}.stage{padding:0 0 24px 58px;}
.stage .circle{position:absolute;left:0;top:0}.stage:not(:last-child):before{left:20px;top:42px;
width:2px;height:calc(100% - 42px)}.eyebrow{margin-top:0}}
"""

JS = """
export default function({data, parentElement}) {
  const root=parentElement.querySelector('.root'); root.replaceChildren();
  function el(tag, cls, text) {const n=document.createElement(tag); if(cls)n.className=cls;
    if(text!=null)n.textContent=text; return n;}
  if(data.mode==='actions') {
    const list=el('ol','steps'); list.setAttribute('aria-label','Your numbered action roadmap');
    data.steps.forEach((s,i)=>{const li=el('li','step');li.append(el('span','circle',i+1));
      const body=el('div');body.append(el('h4','',s.title),el('p','',s.action));
      if(s.done)body.append(el('div','completion','Done when: '+s.done));
      li.append(body);list.append(li);});root.append(list);return;
  }
  const box=el('section','journey');box.setAttribute('aria-label','Your path forward');
  const list=el('ol','stages');list.style.setProperty('--count',data.stages.length);
  const detail=el('div','detail');detail.setAttribute('aria-live','polite');
  function select(index){const s=data.steps[index];detail.replaceChildren(el('h4','',s.title),
    el('p','',s.action),el('p','done','Done when: '+s.done));
    list.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.step===index)));}
  data.stages.forEach((s,i)=>{const li=el('li','stage');li.append(el('div','circle',i+1),
    el('div','eyebrow',s.label),el('h4','',s.title),el('p','',s.caption));
    if(s.step!=null){const b=el('button','','View step '+(s.step+1));b.type='button';
      b.dataset.step=s.step;b.onclick=()=>select(s.step);li.append(b);}list.append(li);});
  box.append(list);if(data.steps.length){box.append(detail);select(0);}root.append(box);
}
"""


def _story(*, data, key):
    # Register in the active runtime, including independent AppTest runtimes.
    component = st.components.v2.component(
        f"career_story_{data['mode']}",
        html='<div class="root"></div>',
        css=CSS,
        js=JS,
        isolate_styles=True,
    )
    return component(data=data, key=key)


def action_rows(milestones, clean=str):
    """Only shorten the topic heading; preserve complete actions and their conditions."""
    rows = []
    for index, item in enumerate(milestones, 1):
        basis = clean(getattr(item, "basis", None) or "").split(";")[0].strip()
        phase = clean(getattr(item, "phase", ""))
        title = basis or (phase if not re.fullmatch(r"Step\s*\d+", phase, re.I) else "")
        rows.append(
            {
                "title": title or f"Action {index}",
                "action": clean(getattr(item, "action", "")),
                "done": clean(getattr(item, "measurable_outcome", "")),
            }
        )
    return rows


def journey_data(plan, milestones, clean=str):
    steps = action_rows(milestones, clean)
    if not steps:
        return {"mode": "journey", "stages": [], "steps": []}
    stages = []
    if getattr(plan, "current_role", None):
        stages.append(
            {
                "label": "Starting point",
                "title": clean(plan.current_role),
                "caption": "Your current career position.",
            }
        )
    stages.append(
        {
            "label": "Next milestone",
            "title": steps[0]["title"],
            "caption": "Begin with the first action in your plan.",
            "step": 0,
        }
    )
    # Link an existing later application/reassessment checkpoint; never invent another action.
    decisions = [
        i
        for i, m in enumerate(milestones)
        if i > 0 and getattr(m, "milestone_type", None) in {"REASSESSMENT", "APPLICATION_READINESS"}
    ]
    if decisions:
        i = decisions[-1]
        stages.append(
            {
                "label": "Decision point",
                "title": "Review your next move",
                "caption": "Follow the conditions in your planned step.",
                "step": i,
            }
        )
    if plan.target_role:
        stages.append(
            {
                "label": "Target direction",
                "title": clean(plan.target_role),
                "caption": "A direction to pursue, not a guaranteed outcome.",
            }
        )
    return {"mode": "journey", "stages": stages, "steps": steps}


def render_journey(plan, milestones=None, *, processing_issue=False, clean=str):
    if processing_issue:
        return
    milestones = plan.milestones if milestones is None else milestones
    data = journey_data(plan, milestones, clean)
    if data["stages"]:
        st.subheader("Your path forward")
        _story(data=data, key="career_journey")


def render_action_story(milestones, *, clean=str):
    if milestones:
        st.subheader("Your action roadmap")
        _story(
            data={"mode": "actions", "steps": action_rows(milestones, clean)},
            key="career_action_story",
        )


def render_competency_list(rows):
    """Compact role-ordered list, with consistent status colours and no evidence prose."""
    frame = pd.DataFrame(rows)
    frame.index = pd.RangeIndex(1, len(frame) + 1, name="#")
    colours = {
        "Demonstrated": ("#226548", "#edf7f0"),
        "Transferable": ("#2851d8", "#edf2ff"),
        "Partially demonstrated": ("#855c20", "#fff6e5"),
        "Unconfirmed": ("#606b7c", "#f2f4f7"),
        "Needs development": ("#973b32", "#fff0ed"),
    }

    def status_style(value):
        ink, fill = colours.get(value, colours["Unconfirmed"])
        return f"color:{ink};background-color:{fill};font-weight:600;text-align:right"

    styled = frame.style.map(status_style, subset=["Your position"]).set_properties(
        **{"padding": "12px", "font-size": "14px"},
    )
    st.table(styled, border="horizontal", hide_index=False)
