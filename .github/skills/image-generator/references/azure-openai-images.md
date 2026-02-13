# Azure OpenAI Image API Reference

## Provisioning

1. Create an Azure OpenAI resource in a supported region (East US, Sweden Central, or West US 3 recommended for image models)
2. Deploy models:
   - **DALL-E 3** — `dall-e-3` model, supports generations only
   - **GPT-4o** — `gpt-4o` model, supports image generation via chat completions (GPT-image-1 capabilities) including editing and variations
3. Copy the endpoint URL and API key from the Azure portal

## Image Generations (DALL-E 3)

```
POST {endpoint}/openai/deployments/{deployment}/images/generations?api-version=2024-06-01
```

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | yes | Max 4000 chars |
| `n` | integer | no | Number of images (DALL-E 3: always 1) |
| `size` | string | no | `1024x1024` (default), `1024x1792`, `1792x1024` |
| `quality` | string | no | `standard` (default), `hd` |
| `response_format` | string | no | `url` (default), `b64_json` |
| `style` | string | no | `natural` (default), `vivid` |

### Response

```json
{
  "created": 1698116700,
  "data": [
    {
      "url": "https://...",
      "revised_prompt": "A detailed description..."
    }
  ]
}
```

## Image Generation via Chat Completions (GPT-4o / GPT-image-1)

GPT-4o with image output supports generation, editing, and variations through the chat completions API.

```
POST {endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-06-01
```

### Generation

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "user", "content": "Generate an image of a sunset over mountains"}
  ],
  "modalities": ["text", "image"],
  "max_tokens": 4096
}
```

### Editing (send image + instruction)

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Change the sky to purple"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }
  ],
  "modalities": ["text", "image"],
  "max_tokens": 4096
}
```

### Vision (analyze image — used by vocabulary builder)

```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Analyze the colors, textures, and art style of this image"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }
  ]
}
```

## Rate Limits

| Model | Requests/min | Images/min |
|-------|-------------|------------|
| DALL-E 3 | 6 | 6 |
| GPT-4o (image) | Varies by tier | Varies |

## Python SDK Usage

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint="https://YOUR-RESOURCE.openai.azure.com/",
    api_key="your-key",
    api_version="2024-06-01"
)

# DALL-E 3 generation
result = client.images.generate(
    model="dall-e-3",
    prompt="a watercolor sunset",
    size="1024x1024",
    quality="hd",
    response_format="b64_json",
    n=1
)

# GPT-4o vision (for vocabulary analysis)
result = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze this image..."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_data}"}}
        ]
    }]
)
```

## Supported Image Formats

- Input: PNG, JPEG, GIF, WebP (for editing/vision)
- Output: PNG (DALL-E 3), PNG/WebP (GPT-4o depending on config)
- Max input size: 20MB
- Input images for editing should be square and ≤4MB for best results
