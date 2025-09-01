# Markdown documentation for Playwright methods used in hover responses
PLAYWRIGHT_DOCS = {
    "goto": """
**page.goto(url: str, **kwargs) -> Response**

Navigates to the given URL.

**Parameters:**
- `url` (str): URL to navigate to
- `timeout` (int, optional): Maximum time in milliseconds, defaults to 30000 (30 seconds)
- `wait_until` (str, optional): When to consider navigation succeeded, one of 'load', 'domcontentloaded', 'networkidle', 'commit'. Defaults to 'load'

**Returns:**
Response: The main resource response. In case of multiple redirects, the navigation will resolve with the response of the last redirect.

**Example:**
```python
await page.goto('https://example.com')
```
""",
    "click": """
**page.click(selector: str, **kwargs) -> None**

Clicks an element matched by the selector.

**Parameters:**
- `selector` (str): Element to click
- `button` (str, optional): Mouse button to use, one of 'left', 'right', 'middle'. Defaults to 'left'
- `click_count` (int, optional): Number of clicks, defaults to 1
- `delay` (int, optional): Time between mousedown and mouseup in milliseconds, defaults to 0
- `position` (dict, optional): A point to click relative to the element's top-left corner
- `timeout` (int, optional): Maximum time in milliseconds, defaults to 30000 (30 seconds)

**Example:**
```python
await page.click('button#submit')
```
""",
    "fill": """
**page.fill(selector: str, value: str, **kwargs) -> None**

Fills an input field with the specified value.

**Parameters:**
- `selector` (str): Input element to fill
- `value` (str): Value to fill into the input field
- `timeout` (int, optional): Maximum time in milliseconds, defaults to 30000 (30 seconds)

**Example:**
```python
await page.fill('input#search', 'query text')
```
""",
    "locator": """
**page.locator(selector: str) -> Locator**

Returns a Locator object that matches the selector.

**Parameters:**
- `selector` (str): Element selector

**Returns:**
Locator: A locator object that can be used for more precise element operations

**Example:**
```python
locator = page.locator('div.article')
await locator.click()
```
""",
    "wait_for_selector": """
**page.wait_for_selector(selector: str, **kwargs) -> ElementHandle**

Waits for the selector to appear on the page.

**Parameters:**
- `selector` (str): Element selector to wait for
- `timeout` (int, optional): Maximum time in milliseconds, defaults to 30000 (30 seconds)
- `state` (str, optional): Wait for element state, one of 'attached', 'detached', 'visible', 'hidden'. Defaults to 'visible'

**Returns:**
ElementHandle: An element handle that can be used for further operations or None if waiting for 'detached' or 'hidden'

**Example:**
```python
button = await page.wait_for_selector('button.ready')
```
""",
    "screenshot": """
**page.screenshot(**kwargs) -> bytes**

Takes a screenshot of the page.

**Parameters:**
- `path` (str, optional): Path where the screenshot will be saved
- `full_page` (bool, optional): When true, takes a screenshot of the full scrollable page. Defaults to False
- `type` (str, optional): Specify screenshot type, can be either 'png' or 'jpeg'. Defaults to 'png'
- `quality` (int, optional): Quality of the image, between 0-100. Only applies when type is 'jpeg'
- `clip` (dict, optional): Clip area of the page to capture

**Returns:**
bytes: Binary image data

**Example:**
```python
await page.screenshot(path='screenshot.png', full_page=True)
```
""",
    "type": """
**page.type(selector: str, text: str, **kwargs) -> None**

Types text into the focused element.

**Parameters:**
- `selector` (str): Element to type into
- `text` (str): Text to type
- `delay` (int, optional): Delay between key presses in milliseconds. Defaults to 0
- `timeout` (int, optional): Maximum time in milliseconds, defaults to 30000 (30 seconds)

**Example:**
```python
await page.type('textarea#editor', 'Hello world!')
```
""",
}
