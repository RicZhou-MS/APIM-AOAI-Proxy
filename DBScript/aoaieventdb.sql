CREATE TABLE [dbo].[AoaiTokenRate](
	[ModelName] [nvarchar](100) NOT NULL,
	[PromptTokenRate] [float] NOT NULL,
	[CompletionTokenRate] [float] NOT NULL
) ON [PRIMARY]
GO

insert into AoaiTokenRate values ('gpt-35-turbo',	1.5E-06, 2E-06)
insert into AoaiTokenRate values ('gpt-35-turbo-16k', 3E-06, 4E-06)
insert into AoaiTokenRate values ('gpt-4',3E-05, 6E-05)
insert into AoaiTokenRate values ('gpt-4-32k',	6E-05, 0.00012)
insert into AoaiTokenRate values ('text-davinci-003', 2E-06, 2E-06)
insert into AoaiTokenRate values ('text-embedding-ada-002', 1E-07,0)
GO

CREATE TABLE [dbo].[ApimAoaiToken](
	[ExecTimeUTC] [datetime] NOT NULL,
	[ExecDateUTC] [datetime] NOT NULL,
	[GatewayRegion] [nvarchar](100) NULL,
	[GatewayServiceName] [nvarchar](150) NULL,
	[SubscriptionId] [nvarchar](50) NULL,
	[SubscriptionName] [nvarchar](100) NULL,
	[UserName] [nvarchar](50) NULL,
	[UserEmail] [nvarchar](50) NULL,
	[ProductName] [nvarchar](100) NULL,
	[ApiName] [nvarchar](100) NULL,
	[OperationId] [nvarchar](100) NULL,
	[ModelName] [nvarchar](100) NULL,
	[IsStreaming] [tinyint] NOT NULL,
	[PromptTokens] [int] NOT NULL,
	[CompletionTokens] [int] NOT NULL,
	[TotalTokens] [int] NOT NULL
) ON [PRIMARY]
GO



/****** Object:  Index [indx_ExecDate]    Script Date: 12/1/2023 4:46:53 PM ******/
CREATE NONCLUSTERED INDEX [indx_ExecDate] ON [dbo].[ApimAoaiToken]
(
	[ExecDateUTC] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, DROP_EXISTING = OFF, ONLINE = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO

/****** Object:  Index [indx_ExecTime]    Script Date: 12/1/2023 4:47:08 PM ******/
CREATE NONCLUSTERED INDEX [indx_ExecTime] ON [dbo].[ApimAoaiToken]
(
	[ExecTimeUTC] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, DROP_EXISTING = OFF, ONLINE = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO

