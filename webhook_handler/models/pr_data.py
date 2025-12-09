from dataclasses import dataclass, field


@dataclass
class PullRequestData:
    """Data class to hold pull request data"""

    number: str
    title: str
    description: str
    url: str
    diff_url: str
    base_branch: str
    base_commit: str
    head_branch: str
    head_commit: str
    owner: str
    repo: str
    id: str = field(init=False)
    image_tag: str = field(init=False)

    def __post_init__(self):
        # ensure description is never None
        if self.description is None:
            self.description = ""
        self.id = f"{self.owner}__{self.repo}-{self.number}"
        self.image_tag = f"image_{self.id}"

    @classmethod
    def from_payload(cls, payload: dict) -> "PullRequestData":
        """
        Extracts data from a pull request or issue payload.

        Parameters:
            payload (dict): A pull request or issue payload

        Returns:
            PullRequestData: The data extracted from the payload
        """
        # Handle both pull_request and issue payloads
        if "pull_request" in payload:
            pr = payload["pull_request"]
        elif "issue" in payload:
            pr = payload["issue"]
        else:
            raise ValueError("Payload must contain either 'pull_request' or 'issue' key")
        
        repo = payload["repository"]
        return cls(
            number=pr["number"],
            title=pr["title"],
            description=pr["body"],
            url=pr["url"],
            diff_url=pr.get("diff_url", ""),  # Issues don't have diff_url
            base_branch=pr["base"]["ref"],
            base_commit=pr["base"]["sha"],
            head_branch=pr["head"]["ref"],
            head_commit=pr["head"]["sha"],
            owner=repo["owner"]["login"],
            repo=repo["name"],
        )
