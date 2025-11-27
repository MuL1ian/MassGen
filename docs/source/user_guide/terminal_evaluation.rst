Terminal Evaluation
===================

MassGen can evaluate its own terminal display and frontend user experience by recording terminal sessions as videos and analyzing them using AI vision models. This is useful for:

* **Frontend development**: Evaluate UI/UX changes to the terminal display
* **Quality assurance**: Verify that status indicators, coordination displays, and agent outputs are clear
* **Case study creation**: Record demos and automatically generate video content
* **User testing**: Analyze how well the terminal communicates agent progress and results

.. note::

   **Quick Setup Summary:**

   1. Install VHS terminal recorder: ``brew install vhs`` (macOS) or ``go install github.com/charmbracelet/vhs@latest``
   2. Ensure OpenAI API key is configured in ``.env``
   3. Use the ``run_massgen_with_recording`` tool in your config
   4. Agent records, analyzes, and provides UX feedback automatically

Quick Start: Try It Now
------------------------

MassGen includes a working example you can try immediately:

.. code-block:: bash

   # Evaluate the terminal display for a simple task
   massgen \
     --config massgen/configs/tools/custom_tools/terminal_evaluation.yaml \
     "Record and evaluate the terminal display for the todo example config"

The agent will:

1. Record a MassGen session running the todo example
2. Save the recording as an MP4 video in the workspace
3. Extract key frames and analyze them with GPT-4.1
4. Provide detailed feedback on terminal display quality

How It Works
------------

The ``run_massgen_with_recording`` tool follows this workflow:

1. **Create VHS Tape**: Generates a VHS script to record the terminal session
2. **Run MassGen**: Executes MassGen WITHOUT ``--automation`` flag (to capture rich terminal display)
3. **Record Video**: VHS records the terminal session as MP4/GIF/WebM
4. **Extract Frames**: Extracts key frames from the video (default: 12 frames)
5. **Analyze Display**: Uses the ``understand_video`` tool to evaluate UX quality
6. **Return Feedback**: Provides structured evaluation with recommendations

The tool automatically saves videos to the agent workspace for reuse in case studies.

Prerequisites
-------------

**1. Install VHS Terminal Recorder**

VHS (by Charm) is required to record terminal sessions:

.. code-block:: bash

   # macOS
   brew install vhs

   # Linux/Windows (requires Go)
   go install github.com/charmbracelet/vhs@latest

Verify installation:

.. code-block:: bash

   vhs --version

**2. OpenAI API Key**

The tool uses GPT-4.1 for video analysis. Ensure your ``.env`` file contains:

.. code-block:: bash

   OPENAI_API_KEY=sk-...

**3. Dependencies**

The ``understand_video`` tool requires ``opencv-python``:

.. code-block:: bash

   pip install opencv-python

Basic Usage
-----------

**Example 1: Evaluate a Simple Config**

.. code-block:: yaml

   # terminal_eval_basic.yaml
   agents:
     - id: "evaluator"
       backend:
         type: "openai"
         model: "gpt-5-mini"
         cwd: "workspace"
         enable_mcp_command_line: true  # Required for VHS
         custom_tools:
           - name: ["run_massgen_with_recording"]
             category: "terminal_evaluation"
             path: "massgen/tool/_multimodal_tools/run_massgen_with_recording.py"
             function: ["run_massgen_with_recording"]
       system_message: |
         You can record and evaluate MassGen terminal displays.
         Use run_massgen_with_recording to test configs and provide UX feedback.

   orchestrator:
     context_paths:
       - path: "massgen/configs/simple_two_agents.yaml"
         permission: "read"

   ui:
     display_type: "rich_terminal"
     logging_enabled: true

Run with:

.. code-block:: bash

   massgen --config terminal_eval_basic.yaml "Evaluate the simple two agents config"

**Example 2: Custom Evaluation Criteria**

You can customize the evaluation prompt to focus on specific aspects:

.. code-block:: python

   # In the agent's prompt or directly in tool call
   run_massgen_with_recording(
       config_path="my_config.yaml",
       question="Create a todo list app",
       evaluation_prompt="""
       Focus on the coordination display. Evaluate:
       1. How clearly does it show agent collaboration?
       2. Are status transitions (streaming → answered → voted) clear?
       3. Is the winner selection process visible?
       4. What improvements would enhance multi-agent visualization?
       """
   )

Tool Parameters
---------------

.. code-block:: python

   async def run_massgen_with_recording(
       config_path: str,
       question: str,
       evaluation_prompt: str = "Evaluate the terminal display quality...",
       output_format: str = "mp4",
       num_frames: int = 12,
       timeout_seconds: int = 300,
       width: int = 1200,
       height: int = 800,
       allowed_paths: Optional[List[str]] = None,
       agent_cwd: Optional[str] = None,
   ) -> ExecutionResult

**Parameters:**

* ``config_path`` (str, required): Path to MassGen config file (YAML)

  * Relative paths resolved relative to agent workspace
  * Absolute paths must be within allowed directories

* ``question`` (str, required): Question to pass to MassGen

* ``evaluation_prompt`` (str): Prompt for evaluating terminal display

  * Default: Comprehensive UX evaluation (clarity, information density, status indicators, user experience)
  * Customize to focus on specific aspects (coordination, readability, etc.)

* ``output_format`` (str): Video format - ``"mp4"`` (default), ``"gif"``, or ``"webm"``

  * MP4: Best quality, suitable for case studies
  * GIF: Smaller file size, easier to embed in docs
  * WebM: Modern web format with good compression

* ``num_frames`` (int): Number of frames to extract for analysis (default: 12)

  * Higher values (16+) provide more detail but increase API costs
  * Lower values (4-8) faster and cheaper but may miss details
  * Recommended: 8-16 frames for most evaluations

* ``timeout_seconds`` (int): Maximum time to wait for MassGen completion (default: 300)

  * Adjust based on task complexity
  * Longer tasks need higher timeouts
  * VHS will wait this long before stopping recording

* ``width`` (int): Terminal width in pixels (default: 1200)
* ``height`` (int): Terminal height in pixels (default: 800)

  * Adjust for your preferred terminal dimensions
  * Larger dimensions capture more detail but increase file size

**Returns:**

.. code-block:: json

   {
     "success": true,
     "operation": "run_massgen_with_recording",
     "config_path": "/path/to/config.yaml",
     "question": "Create a todo list",
     "video_path": "/path/to/workspace/massgen_terminal.mp4",
     "video_format": "mp4",
     "video_size_bytes": 2458624,
     "recording_duration_seconds": 45.3,
     "massgen_timeout_seconds": 300,
     "terminal_dimensions": {"width": 1200, "height": 800},
     "evaluation": {
       "success": true,
       "num_frames_extracted": 12,
       "prompt": "Evaluate the terminal display quality...",
       "response": "The terminal display demonstrates excellent clarity..."
     }
   }

Advanced Usage
--------------

Recording as GIF for Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GIFs are ideal for embedding in documentation and case studies:

.. code-block:: bash

   massgen --config terminal_eval.yaml \
     "Record the todo example as a GIF with focus on agent coordination"

In your agent's system message, guide it to use GIF format:

.. code-block:: text

   When recording for documentation, use output_format="gif" and num_frames=8
   for faster processing and smaller file sizes.

Batch Evaluation of Multiple Configs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can create an agent that systematically evaluates multiple configs:

.. code-block:: yaml

   orchestrator:
     context_paths:
       - path: "massgen/configs/tools/"
         permission: "read"

   agents:
     - id: "batch_evaluator"
       system_message: |
         Evaluate all configs in massgen/configs/tools/ directory.
         For each config:
         1. Record a simple test question
         2. Analyze the terminal display
         3. Compile a comparative report

Integration with Case Studies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tool automatically saves videos to the workspace for case study reuse:

.. code-block:: python

   # Videos are saved as: workspace/massgen_terminal.{format}
   # Reference them in case studies:

   ## Demo Video

   Here's a recording of MassGen solving the task:

   ![Terminal Demo](workspace/massgen_terminal.gif)

   **Evaluation:** The terminal display effectively shows agent collaboration
   with clear status indicators and smooth coordination visualization.

Evaluation Criteria
-------------------

The default evaluation prompt assesses:

1. **Visual Clarity and Readability**

   * Font rendering and contrast
   * Color scheme effectiveness
   * ANSI escape code handling
   * Text layout and spacing

2. **Information Density and Organization**

   * Multi-column layout for parallel agents
   * Content aggregation and streaming display
   * Log message formatting
   * Scroll handling for long outputs

3. **Status Indicator Effectiveness**

   * Agent states (streaming, answered, voted, completed)
   * Progress tracking visibility
   * Coordination phase transitions
   * Winner selection clarity

4. **Overall User Experience**

   * Real-time feedback quality
   * Mental model alignment (does display match user expectations?)
   * Error visibility and handling
   * Cognitive load and information hierarchy

Troubleshooting
---------------

**VHS Not Found Error**

.. code-block:: json

   {
     "success": false,
     "error": "VHS is not installed. Please install it from https://github.com/charmbracelet/vhs"
   }

**Solution:** Install VHS:

.. code-block:: bash

   brew install vhs  # macOS
   go install github.com/charmbracelet/vhs@latest  # Linux/Windows

**Video File Not Created**

If VHS completes but no video file is created:

1. Check VHS stderr output in the error response
2. Verify terminal dimensions are reasonable (width: 800-1920, height: 600-1080)
3. Ensure sufficient disk space for video recording
4. Try a shorter timeout (simpler task)

**Recording Timeout**

.. code-block:: json

   {
     "success": false,
     "error": "VHS recording timed out after 330 seconds"
   }

**Solution:** Increase timeout for complex tasks:

.. code-block:: python

   run_massgen_with_recording(
       config_path="complex_config.yaml",
       question="Complex question",
       timeout_seconds=600  # 10 minutes
   )

**OpenCV Import Error**

.. code-block:: bash

   pip install opencv-python

Best Practices
--------------

1. **Use Appropriate Timeouts**

   * Simple tasks: 60-120 seconds
   * Medium tasks: 120-300 seconds
   * Complex tasks: 300-600 seconds

2. **Optimize Frame Count**

   * Quick evaluation: 4-8 frames
   * Standard evaluation: 8-12 frames
   * Detailed analysis: 12-16 frames

3. **Choose Right Format**

   * Case studies: MP4 (best quality)
   * Documentation: GIF (easy embedding)
   * Web publishing: WebM (modern, efficient)

4. **Customize Evaluation Prompts**

   Focus on specific aspects you're testing:

   * "Evaluate the multi-agent coordination display"
   * "Assess readability for color-blind users"
   * "Analyze information hierarchy and visual flow"

5. **Save Videos for Reference**

   Videos are automatically saved to workspace - commit them to git for:

   * Regression testing (compare old vs new displays)
   * Documentation and tutorials
   * Case study demonstrations
   * User research artifacts

Example Workflow: UI Iteration
-------------------------------

**Step 1: Baseline Evaluation**

.. code-block:: bash

   massgen --config terminal_eval.yaml \
     "Record baseline terminal display for simple_two_agents config"

**Step 2: Make Display Changes**

Edit ``massgen/frontend/displays/terminal_display.py`` to improve UX.

**Step 3: Re-evaluate**

.. code-block:: bash

   massgen --config terminal_eval.yaml \
     "Record updated terminal display for simple_two_agents config"

**Step 4: Compare**

The agent can compare both evaluations and highlight improvements/regressions.

See Also
--------

* :doc:`multimodal` - Other multimodal tools (understand_video, understand_image, understand_audio)
* :doc:`custom_tools` - Creating custom tools for your domain
* :doc:`automation` - Running MassGen in automation mode for backend testing
* :doc:`../development/writing_configs` - Best practices for config development
* Case Study Template: ``docs/case_studies/case-study-template.md``

External Resources
------------------

* `VHS - Charm Terminal Recorder <https://github.com/charmbracelet/vhs>`_
* `VHS Documentation <https://github.com/charmbracelet/vhs/tree/main/docs>`_
* `OpenCV Python Documentation <https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html>`_
