# Syncing Function for Blob and Search Index

This serverless function listens on a Blob Trigger for a file upload/edit event. From the source blob storage, the pertinent file is mounted to a this function job, where several processes happen. First, the document (typically a PDF) is downloaded into memory and analyzed using a form recognizer client (part of the cognitive services suite). The form recognizer allows for pages to be detected, and tables/data structures to be extracted from the form. From there, these items are split into paragraphs and tables as units, and uploaded to a search index using Cognitive Search. Finally, these chunks are uploaded to a target blob storage for safekeeping.

Internal distribution only.

## Environments

### MVP
> _Subscription ID: 98421204-afd5-4b08-9034-29f345261c8b_

_Resources_

| Category | Item |
| ------ | ------ |
|    Resource Group    |   [OpenAINonProd](https://portal.azure.com/#@fortive.onmicrosoft.com/resource/subscriptions/98421204-afd5-4b08-9034-29f345261c8b/resourceGroups/OpenAINonProd/overview)     |
|    Function App    |    [DelphiBlobTrigger](https://portal.azure.com/#@fortive.onmicrosoft.com/resource/subscriptions/98421204-afd5-4b08-9034-29f345261c8b/resourceGroups/openainonprod/providers/Microsoft.Web/sites/DelphiBlobTrigger/appServices)    |
| Function | [BlobTrigger](https://portal.azure.com/#view/WebsitesExtension/FunctionMenuBlade/~/functionOverview/resourceId/%2Fsubscriptions%2F98421204-afd5-4b08-9034-29f345261c8b%2FresourceGroups%2Fopenainonprod%2Fproviders%2FMicrosoft.Web%2Fsites%2FDelphiBlobTrigger%2Ffunctions%2FBlobTrigger) |
| Cognitive Search | [cognitive-search-fort-non-prod](https://portal.azure.com/#@fortive.onmicrosoft.com/resource/subscriptions/98421204-afd5-4b08-9034-29f345261c8b/resourceGroups/OpenAINonProd/providers/Microsoft.Search/searchServices/cognitive-search-fort-non-prod/overview) |
| Search Index | [kataindexnonprod-07-2023-chunked-comprehension](https://portal.azure.com/#view/Microsoft_Azure_Search/Index.ReactView/id/%2Fsubscriptions%2F98421204-afd5-4b08-9034-29f345261c8b%2FresourceGroups%2FOpenAINonProd%2Fproviders%2FMicrosoft.Search%2FsearchServices%2Fcognitive-search-fort-non-prod%23kataindexnonprod-07-2023-chunked-comprehension/location/East%20US/sku/standard) |
| Form Recognizer | [form-recognizer-fort-non-prod](https://portal.azure.com/#@fortive.onmicrosoft.com/resource/subscriptions/98421204-afd5-4b08-9034-29f345261c8b/resourceGroups/OpenAINonProd/providers/Microsoft.CognitiveServices/accounts/form-recognizer-fort-non-prod/overview) |
| CosmosDB | [fortdelphi-database](https://portal.azure.com/#view/Microsoft_Azure_Storage/ContainerMenuBlade/~/overview/storageAccountId/%2Fsubscriptions%2F98421204-afd5-4b08-9034-29f345261c8b%2FresourceGroups%2FOpenAINonProd%2Fproviders%2FMicrosoft.Storage%2FstorageAccounts%2Fblobstorageforsensei/path/fort-delphi-container/etag/%220x8DB77ABA06CC0BC%22/defaultEncryptionScope/%24account-encryption-key/denyEncryptionScopeOverride~/false/defaultId//publicAccessVal/Container) |
| Source Blob Storage Container | [fort-delphi-container](https://portal.azure.com/#view/Microsoft_Azure_Storage/ContainerMenuBlade/~/overview/storageAccountId/%2Fsubscriptions%2F98421204-afd5-4b08-9034-29f345261c8b%2FresourceGroups%2FOpenAINonProd%2Fproviders%2FMicrosoft.Storage%2FstorageAccounts%2Fblobstorageforsensei/path/fort-delphi-container/etag/%220x8DB77ABA06CC0BC%22/defaultEncryptionScope/%24account-encryption-key/denyEncryptionScopeOverride~/false/defaultId//publicAccessVal/Container) |
| Sink Blob Storage Container | [fort-delphi-container-chunks](https://portal.azure.com/#view/Microsoft_Azure_Storage/ContainerMenuBlade/~/overview/storageAccountId/%2Fsubscriptions%2F98421204-afd5-4b08-9034-29f345261c8b%2FresourceGroups%2FOpenAINonProd%2Fproviders%2FMicrosoft.Storage%2FstorageAccounts%2Fblobstorageforsensei/path/fort-delphi-container-chunks/etag/%220x8DB7EFA11CDB74F%22/defaultEncryptionScope/%24account-encryption-key/denyEncryptionScopeOverride~/false/defaultId//publicAccessVal/None) |

_Configuration_

| Key | Description | Initial Value |
| ------ | ------ | -------- |
| AZURE_SINK_STORAGE_CONNECTION_STRING | Connection string for sink storage account, where chunks land. | <_Found under "Access Keys" in "Security + networking" tab for storage account_> |
| AZURE_SOURCE_STORAGE_CONNECTION_STRING | Connection string for source storage account, where documents are sourced. | <_Found under "Access Keys" in "Security + networking" tab for storage account_> |
| AZURE_SINK_CONTAINER | Container name for sink storage. | fort-delphi-container-chunks |
| AZURE_SOURCE_CONTAINER | Container name for source storage. | fort-delphi-container |
| SEARCH_ENDPOINT | Endpoint URL for cognitive search service. | https://cognitive-search-fort-non-prod.search.windows.net |
| SEARCH_API_KEY | Cognitive search API key, to authenticate to endpoint. | <_Found under "Keys" tab for the Cognitive Search service._> |
| AZURE_FORM_RECOGNIZER_ENDPOINT | Form recognizer service endpoint.  | https://form-recognizer-fort-non-prod.cognitiveservices.azure.com/ |
| AZURE_FORM_RECOGNIZER_KEY | Form recognizer access key. | <_Found under "Keys and Endpoint" in "Resource Management" tab._> |
| AZURE_SEARCH_INDEX | Name of search index to connect for cognitive search document retrieval | kataindexnonprod-07-2023-chunked-comprehension |
| VERBOSE_FLAG | Verbose logging flag. | 0 |
| REMOVEALL_FLAG | Flag to remove all blobs from sink blob storage. | 0 |
| REMOVE_FLAG | Flag to remove only subject blobs from sink blob storage. | 0 |
| SKIPBLOBS_FLAG | Flag to skip upload of blobs to sink. | 0 |
| LOCALPDFPARSER | Flag to forego call to form recognizer, and parse PDF data locally. | 0 |
| MODEL_NAME | Name of model token embedding, retrieves count for each chunk. | "gpt-4-32k" |
| COSMOS_DB_CONTAINER | Container name for Cosmos DB, for storing authentication tags for documents. | docembeddingcontainer |
| COSMOS_DB_DATABASE| Database name for security schema in  Cosmos DB. | docembedding |
| COSMOS_DB_PRIMARY_KEY | Primary Access Key for Cosmos DB. | <_Located in "Keys" under the "Settings" tab._> |
| COSMOS_DB_URI | Endpoint URL for Cosmos access. |https://fortdelphi-database.documents.azure.com:443/ |


# Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.com/fortive/fbso-gai-tutor/document-sync.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab.com/fortive/fbso-gai-tutor/document-sync/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/ee/user/project/merge_requests/merge_when_pipeline_succeeds.html)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/index.html)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing(SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***


## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
